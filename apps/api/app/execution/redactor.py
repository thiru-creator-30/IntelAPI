from __future__ import annotations

import re
from typing import Any

_SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "proxy-authorization"}
_SENSITIVE_BODY_KEYS_RE = re.compile(r"(?i)(password|secret|token|api[-_]?key|authorization|cookie)")
_SECRET_VALUE_PLACEHOLDER = "[REDACTED]"


def redact_headers(headers: dict[str, Any] | list[tuple[str, str]] | None) -> dict[str, str]:
    if headers is None:
        return {}
    if isinstance(headers, list):
        headers = {k: v for k, v in headers}
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _SENSITIVE_HEADER_NAMES:
            out[k] = _SECRET_VALUE_PLACEHOLDER
        else:
            out[k] = str(v)
    return out


def redact_body(body: Any) -> Any:
    if body is None:
        return None
    if isinstance(body, dict):
        out = {}
        for k, v in body.items():
            if isinstance(k, str) and _SENSITIVE_BODY_KEYS_RE.search(k):
                out[k] = _SECRET_VALUE_PLACEHOLDER
            else:
                out[k] = redact_body(v)
        return out
    if isinstance(body, list):
        return [redact_body(x) for x in body]
    if isinstance(body, str):
        return body
    return body


def redact_text(text: str, secret_values: list[str] | None = None) -> str:
    out = text
    for s in secret_values or []:
        if s and len(s) >= 4:
            out = out.replace(s, _SECRET_VALUE_PLACEHOLDER)
    return out
