from __future__ import annotations

from google.auth.transport import requests as ga_requests
from google.oauth2 import id_token

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


def verify_google_id_token(token: str) -> dict:
    client_id = get_settings().google_client_id
    if not client_id:
        raise AppError(ErrorCode.INTERNAL_ERROR, "Google sign-in is not configured on this server.")
    try:
        return id_token.verify_oauth2_token(token, ga_requests.Request(), client_id)
    except ValueError as exc:  # invalid/expired token
        raise AppError(ErrorCode.UNAUTHENTICATED, "Invalid Google ID token.", details={"reason": str(exc)}) from exc
