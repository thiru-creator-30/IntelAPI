from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.google import verify_google_id_token
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.security import generate_token, hash_token
from app.db.models import Session as DbSession, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleConfigResponse(BaseModel):
    client_id: str


class GoogleSessionRequest(BaseModel):
    id_token: str


class UserRead(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None

    class Config:
        from_attributes = True


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


@router.get("/google/config", response_model=GoogleConfigResponse)
def google_config() -> GoogleConfigResponse:
    return GoogleConfigResponse(client_id=get_settings().google_client_id)


@router.post("/google/session", response_model=UserRead)
def google_session(req: GoogleSessionRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> UserRead:
    claims = verify_google_id_token(req.id_token)
    sub = claims.get("sub")
    if not sub:
        raise AppError(ErrorCode.UNAUTHENTICATED, "Google token missing sub.")
    email = claims.get("email", "")
    name = claims.get("name") or claims.get("given_name") or None

    user = db.query(User).filter(User.google_sub == sub).first()
    if user is None:
        user = User(google_sub=sub, email=email, display_name=name)
        db.add(user)
        db.flush()
    else:
        if email and user.email != email:
            user.email = email
        if name and user.display_name != name:
            user.display_name = name

    token = generate_token(32)
    tok_hash = hash_token(token)
    settings = get_settings()
    sess = DbSession(
        user_id=user.id,
        token_hash=tok_hash,
        expires_at=_utcnow() + timedelta(seconds=settings.session_ttl_seconds),
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    db.add(sess)
    db.commit()
    db.refresh(user)

    _set_session_cookie(response, token)
    return UserRead(id=str(user.id), email=user.email, display_name=user.display_name)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(id=str(current_user.id), email=current_user.email, display_name=current_user.display_name)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    intelapi_session: Optional[str] = Cookie(default=None, alias=get_settings().session_cookie_name),
) -> dict:
    settings = get_settings()
    if intelapi_session:
        tok_hash = hash_token(intelapi_session)
        sess = db.query(DbSession).filter(DbSession.token_hash == tok_hash, DbSession.revoked_at.is_(None)).first()
        if sess is not None:
            sess.revoked_at = _utcnow()
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}
