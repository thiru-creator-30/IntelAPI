from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.security import constant_time_equal, hash_token
from app.db.models import Project, Session as DbSession, User
from app.db.session import get_db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_bearer_or_cookie(request: Request, cookie_val: Optional[str]) -> Optional[str]:
    # Cookie first; also allow Authorization: Bearer for API clients.
    if cookie_val:
        return cookie_val
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    intelapi_session: Optional[str] = Cookie(default=None, alias=get_settings().session_cookie_name),
) -> User:
    token = _extract_bearer_or_cookie(request, intelapi_session)
    if not token:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Authentication required.")
    tok_hash = hash_token(token)
    sess = db.query(DbSession).filter(DbSession.token_hash == tok_hash).first()
    if sess is None or sess.revoked_at is not None:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Invalid or revoked session.")
    if sess.expires_at < _utcnow():
        raise AppError(ErrorCode.UNAUTHENTICATED, "Session expired.")
    user = db.query(User).filter(User.id == sess.user_id).first()
    if user is None:
        raise AppError(ErrorCode.UNAUTHENTICATED, "User not found.")
    return user


def get_project(project_id: UUID, db: Session, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if project is None or project.archived_at is not None:
        # Existence-hiding: return 404 for cross-tenant or archived-by-default access.
        raise AppError(ErrorCode.NOT_FOUND, "Project not found.")
    return project
