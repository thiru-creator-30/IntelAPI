from __future__ import annotations

from typing import Any


def dedupe_by_request_key(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for c in candidates:
        key = _key(c)
        if key not in seen:
            seen[key] = c
            order.append(key)
    return [seen[k] for k in order]


def _key(c: dict[str, Any]) -> str:
    req = c.get("request_definition") or {}
    return "|".join(
        [
            str(req.get("method", "")).upper(),
            str(req.get("url", "")),
            _headers_key(req.get("headers") or {}),
            str(req.get("body"))[:200],
            str(c.get("kind")),
        ]
    )


def _headers_key(h: dict[str, str]) -> str:
    return ",".join(f"{k.lower()}={v}" for k, v in sorted(h.items()))
