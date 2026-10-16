from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_project
from app.core.errors import AppError, ErrorCode
from app.core.pagination import Page, Paginated, parse_pagination
from app.db.models import EvidenceReference, Finding, Project, User
from app.db.session import get_db

router = APIRouter(tags=["findings"])

USER_EDITABLE_FIELDS = {"triage_status", "user_severity", "user_notes"}
TRIAGE_STATUSES = {"new", "triaging", "accepted", "dismissed"}
SEVERITIES = {None, "info", "low", "medium", "high"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FindingPatch(BaseModel):
    triage_status: str | None = None
    user_severity: str | None = None
    user_notes: str | None = None


@router.get("/projects/{project_id}/findings", response_model=Paginated)
def list_findings(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(Finding).filter(Finding.project_id == project.id)
    total = q.count()
    items = q.order_by(Finding.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(items=[_finding_dict(f) for f in items], pagination=Page(limit=p.limit, offset=p.offset, total=total))


def _finding_dict(f: Finding) -> dict[str, Any]:
    return {
        "id": str(f.id),
        "campaign_id": str(f.campaign_id) if f.campaign_id else None,
        "category": f.category,
        "machine_severity": f.machine_severity,
        "triage_status": f.triage_status,
        "user_severity": f.user_severity,
        "user_notes": f.user_notes,
        "title": f.title,
        "summary": f.summary,
        "evidence_ids": [str(x) for x in (f.evidence_ids or [])],
        "created_at": f.created_at.isoformat(),
        "updated_at": f.updated_at.isoformat(),
    }


@router.get("/findings/{finding_id}")
def get_finding(finding_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    if f is None:
        raise AppError(ErrorCode.NOT_FOUND, "Finding not found.")
    get_project(f.project_id, db, current_user)
    return _finding_dict(f)


@router.patch("/findings/{finding_id}")
def patch_finding(finding_id: UUID, patch: FindingPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    if f is None:
        raise AppError(ErrorCode.NOT_FOUND, "Finding not found.")
    get_project(f.project_id, db, current_user)
    if patch.triage_status is not None:
        if patch.triage_status not in TRIAGE_STATUSES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"invalid triage_status {patch.triage_status}")
        f.triage_status = patch.triage_status
    if patch.user_severity is not None:
        if patch.user_severity not in SEVERITIES:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"invalid user_severity {patch.user_severity}")
        f.user_severity = patch.user_severity
    if patch.user_notes is not None:
        if len(patch.user_notes) > 5000:
            raise AppError(ErrorCode.VALIDATION_ERROR, "user_notes too long")
        f.user_notes = patch.user_notes
    f.updated_at = _utcnow()
    db.commit(); db.refresh(f)
    return _finding_dict(f)


@router.get("/findings/{finding_id}/evidence", response_model=Paginated)
def finding_evidence(finding_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    if f is None:
        raise AppError(ErrorCode.NOT_FOUND, "Finding not found.")
    project = get_project(f.project_id, db, current_user)
    ids = f.evidence_ids or []
    p = parse_pagination(limit, offset)
    q = db.query(EvidenceReference).filter(EvidenceReference.project_id == project.id, EvidenceReference.id.in_(ids)) if ids else db.query(EvidenceReference).filter(EvidenceReference.id == None)  # noqa: E711
    total = q.count()
    items = q.offset(p.offset).limit(p.limit).all()
    return Paginated(items=[_evidence_dict(e) for e in items], pagination=Page(limit=p.limit, offset=p.offset, total=total))


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    e = db.query(EvidenceReference).filter(EvidenceReference.id == evidence_id).first()
    if e is None:
        raise AppError(ErrorCode.NOT_FOUND, "Evidence not found.")
    get_project(e.project_id, db, current_user)
    return _evidence_dict(e)


def _evidence_dict(e: EvidenceReference) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "source_type": e.source_type,
        "source_id": str(e.source_id),
        "provenance": e.provenance,
        "excerpt": e.excerpt,
        "created_at": e.created_at.isoformat(),
    }
