from __future__ import annotations

import json
import re
from typing import Any

from app.execution.service import ExecutionResult

ALLOWED_ASSERTION_TYPES = {"status_code", "latency_ms", "json_path_value", "response_header", "response_schema"}


class AssertionError(TypeError):
    pass


def _json_path_get(data: Any, path: str) -> Any:
    # Minimal JSONPath-ish: dot-separated keys, [index] for arrays.
    cur: Any = data
    token = ""
    i = 0
    path = "$." + path.lstrip("$").lstrip(".")
    while i < len(path):
        ch = path[i]
        if ch == ".":
            token = ""
        elif ch == "[":
            end = path.index("]", i)
            idx = path[i + 1 : end]
            if isinstance(cur, list):
                cur = cur[int(idx)] if idx.isdigit() else None
            elif isinstance(cur, dict):
                cur = cur.get(idx)
            else:
                return None
            i = end
        else:
            token += ch
            if i == len(path) - 1 or path[i + 1] in ".":
                if isinstance(cur, dict):
                    cur = cur.get(token)
                else:
                    return None
                token = ""
        i += 1
    return cur


def _compare(actual: Any, expect: Any) -> bool:
    if isinstance(expect, dict) and "in" in expect and isinstance(expect["in"], list):
        return actual in expect["in"]
    if isinstance(expect, dict) and "contains" in expect:
        return isinstance(actual, str) and expect["contains"] in actual
    if isinstance(expect, dict) and "regex" in expect:
        return isinstance(actual, str) and re.search(expect["regex"], actual) is not None
    return actual == expect


def evaluate_assertion(result: ExecutionResult, assertion: dict[str, Any]) -> dict[str, Any]:
    atype = assertion.get("type")
    cfg = assertion.get("expect") or {}
    if atype not in ALLOWED_ASSERTION_TYPES:
        raise AssertionError(f"unsupported assertion type {atype}")

    passed = False
    actual: Any = None
    message: str | None = None

    if atype == "status_code":
        actual = result.status_code
        passed = _compare(actual, cfg)
        if not passed:
            message = f"expected status {cfg}, got {actual}"
    elif atype == "latency_ms":
        actual = result.duration_ms
        threshold = cfg.get("lte")
        passed = actual is not None and threshold is not None and actual <= threshold
        if not passed:
            message = f"expected latency <= {threshold}ms, got {actual}ms"
    elif atype == "response_header":
        name = cfg.get("name")
        if name:
            actual = result.response_headers.get(name)
            passed = _compare(actual, cfg.get("value"))
        if not passed:
            message = f"expected header {name} to match"
    elif atype == "json_path_value":
        body = {}
        try:
            body = json.loads(result.response_body_excerpt or "{}")
        except Exception:
            passed = False
            message = "response not valid JSON"
        else:
            actual = _json_path_get(body, cfg.get("path", ""))
            passed = _compare(actual, cfg.get("value"))
            if not passed:
                message = f"JSON path '{cfg.get('path')}' expected {cfg.get('value')}, got {actual}"
    elif atype == "response_schema":
        # Lightweight: only checks presence of required keys at top level.
        try:
            body = json.loads(result.response_body_excerpt or "{}")
        except Exception:
            passed = False
            message = "response not valid JSON"
        else:
            required = cfg.get("required", []) or []
            if isinstance(body, dict):
                missing = [k for k in required if k not in body]
                passed = len(missing) == 0
                if not passed:
                    message = f"missing required keys: {missing}"
                    actual = {"missing": missing}
            else:
                passed = False
                message = "response body is not a JSON object"
    return {
        "assertion_type": atype,
        "assertion_config": assertion,
        "passed": bool(passed),
        "actual": actual,
        "message": message,
    }
