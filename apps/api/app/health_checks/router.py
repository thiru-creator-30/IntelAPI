from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analysis.assertions import evaluate_assertion
from app.auth.dependencies import get_current_user, get_project
from app.core.errors import AppError, ErrorCode
from app.core.pagination import Page, Paginated, parse_pagination
from app.db.models import AssertionResult, Execution, HealthCheck, HealthCheckRun, Project, User
from app.db.session import get_db
from app.execution.service import PreparedRequest, execute as run_request
from app.workspace.environments.service import decrypt_var_value, resolve_variables
from app.workspace.router import _load_env_map

router = APIRouter(tags=["health_checks"])
ALLOWED_ASSERTION_TYPES = {"status_code", "latency_ms", "json_path_value", "response_header", "response_schema"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HealthCheckCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    request: dict[str, Any]
    assertions: list[dict[str, Any]]

    def validate_assertions(self) -> None:
        for a in self.assertions:
            if a.get("type") not in ALLOWED_ASSERTION_TYPES:
                raise AppError(ErrorCode.VALIDATION_ERROR, f"unsupported assertion {a.get('type')}")


@router.get("/projects/{project_id}/health-checks", response_model=Paginated)
def list_checks(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(HealthCheck).filter(HealthCheck.project_id == project.id)
    total = q.count()
    items = q.order_by(HealthCheck.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[
            {
                "id": str(c.id), "name": c.name, "request_definition": c.request_definition,
                "assertions": c.assertions, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()
            }
            for c in items
        ],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects/{project_id}/health-checks", status_code=201)
def create_check(project_id: UUID, payload: HealthCheckCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    payload.validate_assertions()
    c = HealthCheck(project_id=project.id, name=payload.name, request_definition=payload.request, assertions=payload.assertions)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": str(c.id), "name": c.name, "request_definition": c.request_definition, "assertions": c.assertions, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()}


def _hc_or_404(db: Session, check_id: UUID, project: Project) -> HealthCheck:
    c = db.query(HealthCheck).filter(HealthCheck.id == check_id, HealthCheck.project_id == project.id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Health check not found.")
    return c


@router.get("/health-checks/{check_id}")
def get_check(check_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Health check not found.")
    get_project(c.project_id, db, current_user)
    return {"id": str(c.id), "name": c.name, "request_definition": c.request_definition, "assertions": c.assertions, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()}


@router.patch("/health-checks/{check_id}")
def update_check(check_id: UUID, payload: HealthCheckCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Health check not found.")
    get_project(c.project_id, db, current_user)
    payload.validate_assertions()
    c.name = payload.name; c.request_definition = payload.request; c.assertions = payload.assertions
    db.commit(); db.refresh(c)
    return {"id": str(c.id), "name": c.name, "request_definition": c.request_definition, "assertions": c.assertions, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()}


@router.delete("/health-checks/{check_id}", status_code=204)
def delete_check(check_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Health check not found.")
    get_project(c.project_id, db, current_user)
    db.delete(c); db.commit()
    return None


@router.post("/health-checks/{check_id}/run")
async def run_check(check_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Health check not found.")
    project = get_project(c.project_id, db, current_user)
    req_def = c.request_definition or {}
    env_id = req_def.get("environment_id")
    env_map = _load_env_map(db, project, env_id) if env_id else {}
    secret_values = [decrypt_var_value(v["value_enc"]) for v in env_map.values() if v.get("is_secret")]
    url, _ = resolve_variables(req_def.get("url", ""), env_map)
    headers = {k: resolve_variables(v, env_map)[0] for k, v in (req_def.get("headers") or {}).items()}
    body = resolve_variables(req_def.get("body") or "", env_map)[0] if req_def.get("body") else None
    pr = PreparedRequest(method=req_def.get("method", "GET").upper(), url=url, headers=headers, body=body, secret_values=secret_values)
    result = await run_request(pr)

    # Persist execution.
    execution = Execution(
        project_id=project.id,
        method=result.request_snapshot.get("method", "GET"),
        url=result.final_url or url,
        request_snapshot=result.request_snapshot,
        outcome=result.outcome,
        status_code=result.status_code,
        duration_ms=result.duration_ms,
        response_headers=result.response_headers,
        response_body_excerpt=result.response_body_excerpt,
        response_size_bytes=result.response_size_bytes,
        transport_error=result.transport_error,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )
    db.add(execution); db.flush()

    assertion_results = []
    passed_all = True
    for a in c.assertions:
        ar_dict = evaluate_assertion(result, a)
        ar = AssertionResult(
            execution_id=execution.id,
            assertion_type=ar_dict["assertion_type"],
            assertion_config=ar_dict["assertion_config"],
            passed=ar_dict["passed"],
            actual=ar_dict["actual"],
            message=ar_dict["message"],
            created_at=_utcnow(),
        )
        db.add(ar)
        assertion_results.append(ar_dict)
        if not ar_dict["passed"]:
            passed_all = False

    run = HealthCheckRun(
        health_check_id=c.id,
        project_id=project.id,
        outcome="pass" if passed_all and result.outcome == "http_response" else "fail" if assertion_results else "error",
        execution_id=execution.id,
        created_at=_utcnow(),
    )
    execution.parent_check_run_id = run.id
    db.add(run)
    db.commit(); db.refresh(run)
    return {
        "run_id": str(run.id),
        "outcome": run.outcome,
        "execution": {
            "id": str(execution.id),
            "outcome": execution.outcome,
            "status_code": execution.status_code,
            "duration_ms": execution.duration_ms,
        },
        "assertion_results": assertion_results,
    }


@router.get("/health-checks/{check_id}/runs", response_model=Paginated)
def list_runs(check_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = db.query(HealthCheck).filter(HealthCheck.id == check_id).first()
    if c is None:
        raise AppError(ErrorCode.NOT_FOUND, "Health check not found.")
    get_project(c.project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(HealthCheckRun).filter(HealthCheckRun.health_check_id == c.id)
    total = q.count()
    items = q.order_by(HealthCheckRun.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[{"id": str(r.id), "outcome": r.outcome, "execution_id": str(r.execution_id), "created_at": r.created_at.isoformat()} for r in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )
