from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_project
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.pagination import Page, Paginated, PaginationParams, parse_pagination
from app.db.models import (
    Collection,
    Environment,
    EnvironmentVariable,
    Execution,
    Project,
    SavedRequest,
    User,
)
from app.db.session import get_db
from app.execution.redactor import redact_headers
from app.execution.service import ExecutionResult as ExecSvcResult, PreparedRequest, execute as run_request
from app.workspace.environments.service import REDACTED_PLACEHOLDER, decrypt_var_value, encrypt_var_value, resolve_variables
from app.workspace.schemas import (
    CollectionCreate,
    CollectionRead,
    EnvironmentCreate,
    EnvironmentRead,
    EnvironmentVariableIn,
    EnvironmentVariableRead,
    ExecuteRequestIn,
    ExecutionOut,
    RequestDefinitionIn,
    SavedRequestRead,
)

router = APIRouter(tags=["workspace"])
log = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_collection_access(db: Session, collection_id: UUID, user: User, project: Project) -> Collection:
    col = db.query(Collection).filter(Collection.id == collection_id, Collection.project_id == project.id).first()
    if col is None:
        raise AppError(ErrorCode.NOT_FOUND, "Collection not found.")
    return col


def _ensure_request_access(db: Session, request_id: UUID, project: Project) -> SavedRequest:
    sr = db.query(SavedRequest).filter(SavedRequest.id == request_id, SavedRequest.project_id == project.id).first()
    if sr is None:
        raise AppError(ErrorCode.NOT_FOUND, "Request not found.")
    return sr


def _ensure_env_access(db: Session, env_id: UUID, project: Project) -> Environment:
    env = db.query(Environment).filter(Environment.id == env_id, Environment.project_id == project.id).first()
    if env is None:
        raise AppError(ErrorCode.NOT_FOUND, "Environment not found.")
    return env


def _load_env_map(db: Session, project: Project, env_id: UUID | None) -> dict[str, dict]:
    if env_id is None:
        return {}
    env = _ensure_env_access(db, env_id, project)
    out: dict[str, dict] = {}
    for v in env.variables:
        out[v.name] = {"value_enc": v.value_enc, "is_secret": v.is_secret, "id": v.id}
    return out


async def _execute(
    db: Session,
    project: Project,
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: str | None,
    env_id: UUID | None,
    saved_request_id: UUID | None,
    parent_check_run_id: UUID | None = None,
    parent_test_case_id: UUID | None = None,
) -> Execution:
    env_map = _load_env_map(db, project, env_id)
    secret_values = []
    for _name, v in env_map.items():
        if v.get("is_secret"):
            try:
                secret_values.append(decrypt_var_value(v["value_enc"]))
            except Exception:
                pass
    resolved_url, _ = resolve_variables(url, env_map)
    resolved_headers: dict[str, str] = {}
    for k, v in headers.items():
        rv, _ = resolve_variables(v, env_map)
        resolved_headers[k] = rv
    resolved_body = body
    if body:
        resolved_body, _ = resolve_variables(body, env_map)

    pr = PreparedRequest(
        method=method.upper(),
        url=resolved_url,
        headers=resolved_headers,
        body=resolved_body,
        secret_values=secret_values,
    )
    svc_result: ExecSvcResult = await run_request(pr)

    # Persist immutable snapshot.
    execution = Execution(
        project_id=project.id,
        saved_request_id=saved_request_id,
        parent_check_run_id=parent_check_run_id,
        parent_test_case_id=parent_test_case_id,
        method=svc_result.request_snapshot.get("method", method.upper()),
        url=svc_result.final_url or resolved_url,
        request_snapshot=svc_result.request_snapshot,
        outcome=svc_result.outcome,
        status_code=svc_result.status_code,
        duration_ms=svc_result.duration_ms,
        response_headers=svc_result.response_headers,
        response_body_excerpt=svc_result.response_body_excerpt,
        response_size_bytes=svc_result.response_size_bytes,
        transport_error=svc_result.transport_error,
        started_at=svc_result.started_at,
        completed_at=svc_result.completed_at,
        created_at=_utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


# --- Collections ---
@router.get("/projects/{project_id}/collections", response_model=Paginated)
def list_collections(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(Collection).filter(Collection.project_id == project.id)
    total = q.count()
    items = q.order_by(Collection.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[CollectionRead.model_validate(x).model_dump(mode="json") for x in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects/{project_id}/collections", response_model=CollectionRead, status_code=201)
def create_collection(project_id: UUID, payload: CollectionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    col = Collection(project_id=project.id, name=payload.name)
    db.add(col); db.commit(); db.refresh(col)
    return CollectionRead.model_validate(col)


@router.get("/collections/{collection_id}", response_model=CollectionRead)
def get_collection(collection_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if col is None:
        raise AppError(ErrorCode.NOT_FOUND, "Collection not found.")
    project = get_project(col.project_id, db, current_user)  # ensures ownership
    return CollectionRead.model_validate(col)


@router.patch("/collections/{collection_id}", response_model=CollectionRead)
def update_collection(collection_id: UUID, payload: CollectionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if col is None:
        raise AppError(ErrorCode.NOT_FOUND, "Collection not found.")
    get_project(col.project_id, db, current_user)
    col.name = payload.name
    db.commit(); db.refresh(col)
    return CollectionRead.model_validate(col)


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if col is None:
        raise AppError(ErrorCode.NOT_FOUND, "Collection not found.")
    get_project(col.project_id, db, current_user)
    db.delete(col); db.commit()
    return None


# --- Saved requests ---
@router.get("/projects/{project_id}/requests", response_model=Paginated)
def list_requests(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(SavedRequest).filter(SavedRequest.project_id == project.id)
    total = q.count()
    items = q.order_by(SavedRequest.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[SavedRequestRead.model_validate(x).model_dump(mode="json") for x in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects/{project_id}/requests", response_model=SavedRequestRead, status_code=201)
def create_request(project_id: UUID, payload: RequestDefinitionIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    if payload.collection_id is not None:
        _ensure_collection_access(db, payload.collection_id, current_user, project)
    if payload.environment_id is not None:
        _ensure_env_access(db, payload.environment_id, project)
    sr = SavedRequest(
        project_id=project.id,
        collection_id=payload.collection_id,
        name=payload.name,
        method=payload.method.upper(),
        url=payload.url,
        headers=redact_headers(payload.headers),
        body=payload.body,
        environment_id=payload.environment_id,
    )
    db.add(sr); db.commit(); db.refresh(sr)
    return SavedRequestRead.model_validate(sr)


@router.get("/requests/{request_id}", response_model=SavedRequestRead)
def get_request(request_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sr = db.query(SavedRequest).filter(SavedRequest.id == request_id).first()
    if sr is None:
        raise AppError(ErrorCode.NOT_FOUND, "Request not found.")
    get_project(sr.project_id, db, current_user)
    return SavedRequestRead.model_validate(sr)


@router.patch("/requests/{request_id}", response_model=SavedRequestRead)
def update_request(request_id: UUID, payload: RequestDefinitionIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sr = _ensure_request_safe(db, request_id, current_user)
    sr.name = payload.name; sr.method = payload.method.upper(); sr.url = payload.url; sr.headers = redact_headers(payload.headers); sr.body = payload.body
    sr.environment_id = payload.environment_id; sr.collection_id = payload.collection_id
    db.commit(); db.refresh(sr)
    return SavedRequestRead.model_validate(sr)


def _ensure_request_safe(db: Session, request_id: UUID, current_user: User) -> SavedRequest:
    sr = db.query(SavedRequest).filter(SavedRequest.id == request_id).first()
    if sr is None:
        raise AppError(ErrorCode.NOT_FOUND, "Request not found.")
    get_project(sr.project_id, db, current_user)
    return sr


@router.delete("/requests/{request_id}", status_code=204)
def delete_request(request_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sr = _ensure_request_safe(db, request_id, current_user)
    db.delete(sr); db.commit()
    return None


# --- Execute ---
@router.post("/requests/execute", response_model=ExecutionOut)
async def execute_request_route(payload: ExecuteRequestIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # If saved_request_id is provided, it determines the project; otherwise url-based execution
    # requires the caller to already have an inferred project context. We require an existing saved
    # request OR an ad-hoc execution scoped to a project via a header `x-project-id` to keep ownership.
    project_id: UUID | None = None
    if payload.saved_request_id:
        sr = db.query(SavedRequest).filter(SavedRequest.id == payload.saved_request_id).first()
        if sr is None:
            raise AppError(ErrorCode.NOT_FOUND, "Saved request not found.")
        project_id = sr.project_id
        method = payload.method if payload.method else sr.method
        url = payload.url if payload.url else sr.url
        headers = payload.headers or sr.headers
        body = payload.body if payload.body is not None else sr.body
        env_id = payload.environment_id if payload.environment_id else sr.environment_id
    else:
        raise AppError(ErrorCode.VALIDATION_ERROR, "saved_request_id is required for execution in MVP.")
    project = get_project(project_id, db, current_user)
    execution = await _execute(
        db,
        project,
        method=method,
        url=url,
        headers=headers,
        body=body,
        env_id=env_id,
        saved_request_id=sr.id if payload.saved_request_id else None,
    )
    return ExecutionOut.model_validate(execution)


# --- History ---
@router.get("/projects/{project_id}/history", response_model=Paginated)
def history(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(Execution).filter(Execution.project_id == project.id, Execution.parent_check_run_id.is_(None), Execution.parent_test_case_id.is_(None))
    total = q.count()
    items = q.order_by(Execution.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[ExecutionOut.model_validate(x).model_dump(mode="json") for x in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.get("/executions/{execution_id}", response_model=ExecutionOut)
def get_execution(execution_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ex = db.query(Execution).filter(Execution.id == execution_id).first()
    if ex is None:
        raise AppError(ErrorCode.NOT_FOUND, "Execution not found.")
    get_project(ex.project_id, db, current_user)
    return ExecutionOut.model_validate(ex)


# --- Environments ---
@router.get("/projects/{project_id}/environments", response_model=Paginated)
def list_envs(project_id: UUID, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    p = parse_pagination(limit, offset)
    q = db.query(Environment).filter(Environment.project_id == project.id)
    total = q.count()
    items = q.order_by(Environment.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[_env_read(x).model_dump(mode="json") for x in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects/{project_id}/environments", response_model=EnvironmentRead, status_code=201)
def create_env(project_id: UUID, payload: EnvironmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project(project_id, db, current_user)
    env = Environment(project_id=project.id, name=payload.name)
    db.add(env); db.commit(); db.refresh(env)
    return _env_read(env)


@router.get("/environments/{environment_id}", response_model=EnvironmentRead)
def get_env(environment_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if env is None:
        raise AppError(ErrorCode.NOT_FOUND, "Environment not found.")
    get_project(env.project_id, db, current_user)
    return _env_read(env)


@router.patch("/environments/{environment_id}", response_model=EnvironmentRead)
def update_env(environment_id: UUID, payload: EnvironmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if env is None:
        raise AppError(ErrorCode.NOT_FOUND, "Environment not found.")
    get_project(env.project_id, db, current_user)
    env.name = payload.name
    db.commit(); db.refresh(env)
    return _env_read(env)


@router.delete("/environments/{environment_id}", status_code=204)
def delete_env(environment_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if env is None:
        raise AppError(ErrorCode.NOT_FOUND, "Environment not found.")
    get_project(env.project_id, db, current_user)
    db.delete(env); db.commit()
    return None


@router.post("/environments/{environment_id}/variables", response_model=EnvironmentVariableRead, status_code=201)
def add_env_var(environment_id: UUID, payload: EnvironmentVariableIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if env is None:
        raise AppError(ErrorCode.NOT_FOUND, "Environment not found.")
    get_project(env.project_id, db, current_user)
    existing = db.query(EnvironmentVariable).filter(EnvironmentVariable.environment_id == env.id, EnvironmentVariable.name == payload.name).first()
    if existing:
        existing.value_enc = encrypt_var_value(payload.value)
        existing.is_secret = payload.is_secret
        db.commit(); db.refresh(existing)
        v = existing
    else:
        v = EnvironmentVariable(environment_id=env.id, name=payload.name, value_enc=encrypt_var_value(payload.value), is_secret=payload.is_secret)
        db.add(v); db.commit(); db.refresh(v)
    return _var_read(v)


@router.delete("/environments/{environment_id}/variables/{variable_id}", status_code=204)
def delete_env_var(environment_id: UUID, variable_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if env is None:
        raise AppError(ErrorCode.NOT_FOUND, "Environment not found.")
    get_project(env.project_id, db, current_user)
    v = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == variable_id, EnvironmentVariable.environment_id == env.id).first()
    if v is None:
        raise AppError(ErrorCode.NOT_FOUND, "Variable not found.")
    db.delete(v); db.commit()
    return None


def _var_read(v: EnvironmentVariable) -> EnvironmentVariableRead:
    return EnvironmentVariableRead(
        id=v.id,
        name=v.name,
        value=REDACTED_PLACEHOLDER if v.is_secret else decrypt_var_value(v.value_enc),
        is_secret=v.is_secret,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


def _env_read(env: Environment) -> EnvironmentRead:
    return EnvironmentRead(
        id=env.id,
        project_id=env.project_id,
        name=env.name,
        variables=[_var_read(v) for v in env.variables],
        created_at=env.created_at,
        updated_at=env.updated_at,
    )
