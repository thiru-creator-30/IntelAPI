from __future__ import annotations

import logging
import re
import sys
from typing import Any, Iterable
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(authorization|cookie|set-cookie|api[-_]?key|token|secret|password)\s*[:=]\s*\S+"),
]


def _redact_value(v: Any) -> Any:
    if isinstance(v, str):
        out = v
        for pat in _SECRET_PATTERNS:
            out = pat.sub(lambda m: m.group(0).split(":", 1)[0] + ":[REDACTED]" if ":" in m.group(0) else m.group(0)[:3] + "...[REDACTED]", out)
        return out
    if isinstance(v, dict):
        return {
            k: "[REDACTED]" if isinstance(k, str) and k.lower() in _SENSITIVE_HEADERS else _redact_value(val)
            for k, val in v.items()
        }
    if isinstance(v, list):
        return [_redact_value(x) for x in v]
    return v


def redact_for_log(event: dict[str, Any]) -> dict[str, Any]:
    return _redact_value(event)


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_for_log,
            structlog.dev.ConsoleRenderer() if sys.stderr.isatty() else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
