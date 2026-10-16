from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api_understanding.normalizer import normalize_operations
from app.api_understanding.parser import parse_spec
from app.auth.dependencies import get_current_user, get_project
from app.core.errors import AppError, ErrorCode
from app.core.pagination import Page, Paginated, PaginationParams, parse_pagination
from app.core.security import hash_sha256
from app.db.models import ApiOperation, ApiSpecification, KnowledgeFact, Project, User
from app.db.session import get_db
from app.execution.service import fetch_bytes
from app.knowledge.facts import facts_from_operation, facts_from_spec
from app.test_generation.deduplication import dedupe_by_request_key
from app.test_generation.deterministic import generate_candidates

router = APIRouter(tags=["api_understanding"])


class CandidatePreviewOut(BaseModel):
    items: list[dict]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/projects/{project_id}/specifications", response_model=Paginated)
def list_specs(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(ApiSpecification).filter(ApiSpecification.project_id == project.id)
    total = q.count()
    items = q.order_by(ApiSpecification.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[
            {
                "id": str(s.id),
                "title": s.title,
                "version": s.version,
                "source_type": s.source_type,
                "source_url": s.source_url,
                "size_bytes": s.size_bytes,
                "created_at": s.created_at.isoformat(),
            }
            for s in items
        ],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects/{project_id}/specifications/import")
async def import_spec(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
):
    project = get_project(project_id, db, current_user)
    if file is None and not url:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Provide file or url.")
    if file is not None and url:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Provide either file or url, not both.")

    raw: bytes
    source_type: str
    source_url_val: str | None = None
    if file is not None:
        raw = await file.read()
        source_type = "file"
    else:
        source_type = "url"
        source_url_val = url
        raw = await fetch_bytes(url or "")

    doc = parse_spec(raw)
    content_hash = hash_sha256(raw)
    info = doc.get("info") or {}
    spec = ApiSpecification(
        project_id=project.id,
        source_type=source_type,
        source_url=source_url_val,
        title=info.get("title"),
        version=info.get("version"),
        spec_json=doc,
        content_hash=content_hash,
        spec_format="openapi_3",
        size_bytes=len(raw),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(spec)
    db.flush()

    # Persist facts and operations
    for f in facts_from_spec(doc, spec.id):
        db.add(KnowledgeFact(project_id=project.id, provenance=f["provenance"], fact_type=f["fact_type"], subject_type=f["subject_type"], subject_id=f["subject_id"], payload=f["payload"], created_at=_utcnow()))

    ops = normalize_operations(doc)
    for op in ops:
        op_id = uuid4()
        db.add(
            ApiOperation(
                id=op_id,
                specification_id=spec.id,
                project_id=project.id,
                method=op["method"],
                path=op["path"],
                operation_id=op["operation_id"],
                summary=op.get("summary"),
                normalized=op,
                created_at=_utcnow(),
            )
        )
        for f in facts_from_operation(op, op_id, spec.id):
            db.add(KnowledgeFact(project_id=project.id, provenance=f["provenance"], fact_type=f["fact_type"], subject_type=f["subject_type"], subject_id=f["subject_id"], payload=f["payload"], created_at=_utcnow()))

    db.commit()
    db.refresh(spec)
    return {
        "id": str(spec.id),
        "title": spec.title,
        "version": spec.version,
        "operations_count": len(ops),
        "created_at": spec.created_at.isoformat(),
    }


@router.get("/specifications/{specification_id}")
def get_spec(specification_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    spec = db.query(ApiSpecification).filter(ApiSpecification.id == specification_id).first()
    if spec is None:
        raise AppError(ErrorCode.NOT_FOUND, "Specification not found.")
    get_project(spec.project_id, db, current_user)
    return {
        "id": str(spec.id),
        "title": spec.title,
        "version": spec.version,
        "source_type": spec.source_type,
        "source_url": spec.source_url,
        "size_bytes": spec.size_bytes,
        "spec_json": spec.spec_json,
        "created_at": spec.created_at.isoformat(),
    }


@router.get("/specifications/{specification_id}/operations", response_model=Paginated)
def list_operations(specification_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    spec = db.query(ApiSpecification).filter(ApiSpecification.id == specification_id).first()
    if spec is None:
        raise AppError(ErrorCode.NOT_FOUND, "Specification not found.")
    get_project(spec.project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(ApiOperation).filter(ApiOperation.specification_id == spec.id)
    total = q.count()
    items = q.order_by(ApiOperation.path, ApiOperation.method).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[
            {
                "id": str(o.id),
                "method": o.method,
                "path": o.path,
                "operation_id": o.operation_id,
                "summary": o.summary,
            }
            for o in items
        ],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.get("/operations/{operation_id}")
def get_operation(operation_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    op = db.query(ApiOperation).filter(ApiOperation.id == operation_id).first()
    if op is None:
        raise AppError(ErrorCode.NOT_FOUND, "Operation not found.")
    get_project(op.project_id, db, current_user)
    return {
        "id": str(op.id),
        "method": op.method,
        "path": op.path,
        "operation_id": op.operation_id,
        "summary": op.summary,
        "normalized": op.normalized,
        "specification_id": str(op.specification_id),
    }


@router.post("/operations/{operation_id}/candidates/preview", response_model=CandidatePreviewOut)
def preview_candidates(operation_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    op = db.query(ApiOperation).filter(ApiOperation.id == operation_id).first()
    if op is None:
        raise AppError(ErrorCode.NOT_FOUND, "Operation not found.")
    get_project(op.project_id, db, current_user)
    # Non-persisting preview: use a random campaign_id for stable ID hashing, do not persist.
    dummy_campaign_id = uuid4()
    candidates = generate_candidates(campaign_id=dummy_campaign_id, operation=op.normalized, operation_id=op.id)
    candidates = dedupe_by_request_key(candidates)
    return CandidatePreviewOut(items=candidates)
