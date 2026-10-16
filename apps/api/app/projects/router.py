from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_project
from app.core.errors import AppError, ErrorCode
from app.core.pagination import Page, Paginated, PaginationParams, parse_pagination
from app.db.models import (
    AssertionResult,
    Campaign,
    Execution,
    Finding,
    Project,
    TestCase,
    User,
)
from app.db.session import get_db
from app.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(tags=["projects"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/projects", response_model=Paginated)
def list_projects(
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Paginated:
    p = parse_pagination(limit, offset)
    q = db.query(Project).filter(Project.owner_id == current_user.id, Project.archived_at.is_(None))
    total = q.count()
    items = q.order_by(Project.created_at.desc()).offset(p.offset).limit(p.limit).all()
    return Paginated(
        items=[ProjectRead.model_validate(x).model_dump(mode="json") for x in items],
        pagination=Page(limit=p.limit, offset=p.offset, total=total),
    )


@router.post("/projects", response_model=ProjectRead, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = Project(owner_id=current_user.id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectRead.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project_route(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project(project_id, db, current_user)
    return ProjectRead.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project(project_id, db, current_user)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    db.commit()
    db.refresh(project)
    return ProjectRead.model_validate(project)


@router.post("/projects/{project_id}/archive", response_model=ProjectRead)
def archive_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project(project_id, db, current_user)
    project.archived_at = _utcnow()
    db.commit()
    db.refresh(project)
    return ProjectRead.model_validate(project)


@router.get("/projects/{project_id}/overview")
def project_overview(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    project = get_project(project_id, db, current_user)
    executions_count = db.query(Execution).filter(Execution.project_id == project.id).count()
    campaigns_count = db.query(Campaign).filter(Campaign.project_id == project.id).count()
    findings_count = db.query(Finding).filter(Finding.project_id == project.id).count()
    tests_count = db.query(TestCase).filter(TestCase.project_id == project.id).count()
    pass_count = (
        db.query(AssertionResult).join(Execution, AssertionResult.execution_id == Execution.id)
        .filter(Execution.project_id == project.id, AssertionResult.passed.is_(True))
        .count()
    )
    fail_count = (
        db.query(AssertionResult).join(Execution, AssertionResult.execution_id == Execution.id)
        .filter(Execution.project_id == project.id, AssertionResult.passed.is_(False))
        .count()
    )
    last_execution = (
        db.query(Execution).filter(Execution.project_id == project.id).order_by(Execution.created_at.desc()).first()
    )
    return {
        "project": ProjectRead.model_validate(project).model_dump(mode="json"),
        "counts": {
            "executions": executions_count,
            "campaigns": campaigns_count,
            "findings": findings_count,
            "tests": tests_count,
            "assertions_passed": pass_count,
            "assertions_failed": fail_count,
        },
        "last_execution_at": last_execution.created_at.isoformat() if last_execution else None,
    }
