from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adaptive.scoring import score_next_tests
from app.auth.dependencies import get_current_user, get_project
from app.core.errors import AppError, ErrorCode
from app.core.pagination import Page, Paginated, parse_pagination
from app.campaigns.schemas import CampaignCreate, CampaignRead
from app.campaigns.state_machine import can_transition, is_terminal
from app.db.models import (
    ApiOperation,
    AssertionResult,
    Campaign,
    CampaignEvent,
    CampaignJob,
    Execution,
    Finding,
    Project,
    TestCase,
    User,
)
from app.db.session import get_db
from app.test_generation.deduplication import dedupe_by_request_key
from app.test_generation.deterministic import generate_candidates

router = APIRouter(tags=["campaigns"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _add_event(db: Session, campaign_id: UUID, event_type: str, payload: dict[str, Any]) -> None:
    db.add(CampaignEvent(campaign_id=campaign_id, event_type=event_type, payload=payload, created_at=_utcnow()))


@router.get("/projects/{project_id}/campaigns", response_model=Paginated)
def list_campaigns(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(Campaign).filter(Campaign.project_id == project.id)
    total = q.count()
    items = q.order_by(Campaign.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[CampaignRead.model_validate(c).model_dump(mode="json") for c in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects/{project_id}/campaigns", status_code=202)
def create_campaign(project_id: UUID, payload: CampaignCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    if payload.source_specification_id is None and payload.source_operation_id is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Provide source_specification_id or source_operation_id.")

    c = Campaign(
        project_id=project.id,
        name=payload.name,
        source_specification_id=payload.source_specification_id,
        source_operation_id=payload.source_operation_id,
        state="queued",
        budget_executions=payload.budget_executions,
        executions_used=0,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(c)
    db.flush()
    job = CampaignJob(campaign_id=c.id, created_at=_utcnow(), updated_at=_utcnow())
    db.add(job)
    _add_event(db, c.id, "created", {"budget": payload.budget_executions})

    # Pre-seed deterministic test cases.
    operations: list[ApiOperation] = []
    if payload.source_operation_id:
        op = db.query(ApiOperation).filter(ApiOperation.id == payload.source_operation_id, ApiOperation.project_id == project.id).first()
        if op is None:
            raise AppError(ErrorCode.NOT_FOUND, "Operation not found.")
        operations = [op]
    elif payload.source_specification_id:
        ops = db.query(ApiOperation).filter(ApiOperation.specification_id == payload.source_specification_id, ApiOperation.project_id == project.id).all()
        operations = list(ops)

    all_candidates: list[dict[str, Any]] = []
    for op in operations:
        all_candidates.extend(generate_candidates(campaign_id=c.id, operation=op.normalized, operation_id=op.id))
    all_candidates = dedupe_by_request_key(all_candidates)
    for cand in all_candidates[: payload.budget_executions]:
        tc = TestCase(
            id=UUID(cand["id"]),
            campaign_id=c.id,
            project_id=project.id,
            source_operation_id=_op_id_for(cand),
            kind=cand["kind"],
            request_definition=cand["request_definition"],
            assertions=cand.get("assertions", []),
            provenance=cand.get("provenance", {}),
            created_at=_utcnow(),
        )
        db.add(tc)

    db.commit()
    db.refresh(c)
    return CampaignRead.model_validate(c)


def _op_id_for(cand: dict[str, Any]) -> UUID | None:
    pid = (cand.get("provenance") or {}).get("operation_id")
    try:
        return UUID(pid) if pid else None
    except Exception:
        return None


@router.get("/campaigns/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Campaign not found.")
    get_project(c.project_id, db, current_user)
    return CampaignRead.model_validate(c)


@router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignRead)
def cancel_campaign(campaign_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Campaign not found.")
    get_project(c.project_id, db, current_user)
    if is_terminal(c.state):
        # Idempotent: return unchanged.
        return CampaignRead.model_validate(c)
    if not can_transition(c.state, "cancelled"):
        raise AppError(ErrorCode.CONFLICT, f"Cannot cancel campaign in state {c.state}")
    c.state = "cancelled"
    c.completed_at = _utcnow()
    c.updated_at = _utcnow()
    _add_event(db, c.id, "cancelled", {})
    db.commit(); db.refresh(c)
    return CampaignRead.model_validate(c)


def _paginated_items(query, params, mapper):
    total = query.count()
    items = query.order_by(None).order_by(None)  # caller sets order
    return Paginated(items=[mapper(x) for x in items.offset(params.offset).limit(params.limit).all()], pagination=Page(limit=params.limit, offset=params.offset, total=total))


@router.get("/campaigns/{campaign_id}/tests", response_model=Paginated)
def list_tests(campaign_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Campaign not found.")
    get_project(c.project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(TestCase).filter(TestCase.campaign_id == c.id).order_by(TestCase.created_at.asc())
    total = q.count()
    items = q.offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[{
            "id": str(t.id), "kind": t.kind, "request_definition": t.request_definition,
            "assertions": t.assertions, "provenance": t.provenance, "created_at": t.created_at.isoformat()
        } for t in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.get("/campaigns/{campaign_id}/executions", response_model=Paginated)
def list_campaign_executions(campaign_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Campaign not found.")
    get_project(c.project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(Execution).filter(Execution.parent_test_case_id.isnot(None)).join(TestCase, TestCase.id == Execution.parent_test_case_id).filter(TestCase.campaign_id == c.id)
    total = q.count()
    items = q.order_by(Execution.started_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[{
            "id": str(e.id), "outcome": e.outcome, "status_code": e.status_code, "duration_ms": e.duration_ms,
            "url": e.url, "method": e.method, "started_at": e.started_at.isoformat(), "completed_at": e.completed_at.isoformat(),
        } for e in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.get("/campaigns/{campaign_id}/events", response_model=Paginated)
def list_events(campaign_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Campaign not found.")
    get_project(c.project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(CampaignEvent).filter(CampaignEvent.campaign_id == c.id).order_by(CampaignEvent.created_at.asc())
    total = q.count()
    items = q.offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[{"id": str(e.id), "event_type": e.event_type, "payload": e.payload, "created_at": e.created_at.isoformat()} for e in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.get("/campaigns/{campaign_id}/report")
def campaign_report(campaign_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Campaign not found.")
    get_project(c.project_id, db, current_user)
    tests_total = db.query(TestCase).filter(TestCase.campaign_id == c.id).count()
    execs_q = db.query(Execution).join(TestCase, TestCase.id == Execution.parent_test_case_id).filter(TestCase.campaign_id == c.id)
    execs_total = execs_q.count()
    findings_total = db.query(Finding).filter(Finding.campaign_id == c.id).count()
    pass_count = db.query(AssertionResult).join(Execution, AssertionResult.execution_id == Execution.id).join(TestCase, TestCase.id == Execution.parent_test_case_id).filter(TestCase.campaign_id == c.id, AssertionResult.passed.is_(True)).count()
    fail_count = db.query(AssertionResult).join(Execution, AssertionResult.execution_id == Execution.id).join(TestCase, TestCase.id == Execution.parent_test_case_id).filter(TestCase.campaign_id == c.id, AssertionResult.passed.is_(False)).count()
    events_q = db.query(CampaignEvent).filter(CampaignEvent.campaign_id == c.id).order_by(CampaignEvent.created_at.asc())
    events = [{"id": str(e.id), "event_type": e.event_type, "payload": e.payload, "created_at": e.created_at.isoformat()} for e in events_q.all()]
    return {
        "campaign": CampaignRead.model_validate(c).model_dump(mode="json"),
        "tests_total": tests_total,
        "executions_total": execs_total,
        "findings_total": findings_total,
        "assertions_passed": pass_count,
        "assertions_failed": fail_count,
        "events": events,
        "partial": c.state != "completed" or findings_total > 0,
    }
