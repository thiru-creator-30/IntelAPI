from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode

MAX_URL_LEN = 8192
MAX_BODY_BYTES = 1024 * 1024  # 1 MiB candidate body cap
FORBIDDEN_HEADERS = {"host", "cookie", "authorization", "proxy-authorization", "content-length", "transfer-encoding"}


def validate_candidate(c: dict) -> None:
    req = c.get("request_definition") or {}
    url = req.get("url", "")
    if not isinstance(url, str) or not url:
        raise AppError(ErrorCode.VALIDATION_ERROR, "candidate missing url")
    if len(url) > MAX_URL_LEN:
        raise AppError(ErrorCode.VALIDATION_ERROR, "candidate url too long")
    method = (req.get("method") or "").upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"invalid candidate method {method}")
    headers = req.get("headers") or {}
    for h in headers:
        if h.lower() in FORBIDDEN_HEADERS:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"candidate header '{h}' is not allowed")
    body = req.get("body")
    if body is not None:
        if isinstance(body, str):
            if len(body.encode("utf-8", errors="replace")) > MAX_BODY_BYTES:
                raise AppError(ErrorCode.VALIDATION_ERROR, "candidate body too large")
        else:
            if len(("" if body is None else str(body)).encode("utf-8")) > MAX_BODY_BYTES:
                raise AppError(ErrorCode.VALIDATION_ERROR, "candidate body too large")
    assertions = c.get("assertions") or []
    if not isinstance(assertions, list):
        raise AppError(ErrorCode.VALIDATION_ERROR, "candidate assertions must be a list")
    for a in assertions:
        if a.get("type") not in {"status_code", "latency_ms", "json_path_value", "response_header", "response_schema"}:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"unsupported assertion type {a.get('type')}")
