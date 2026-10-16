from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.test_generation.validation import validate_candidate


def _stable_id(campaign_id: UUID, seed: str) -> str:
    h = hashlib.sha256((str(campaign_id) + "|" + seed).encode("utf-8")).hexdigest()[:24]
    return str(UUID(h[:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:32]))


def _base_url(op: dict[str, Any]) -> str:
    base = (op.get("base_url") or "").rstrip("/")
    return base or ""


def _render_path(path: str, path_params: dict[str, Any]) -> str:
    out = path
    for name, val in path_params.items():
        out = out.replace("{" + name + "}", str(val))
    return out


def _example_for_schema(schema: dict[str, Any], required: bool = True) -> Any:
    if not schema:
        return None
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    t = schema.get("type")
    fmt = schema.get("format")
    if t == "integer":
        return schema.get("minimum", 0)
    if t == "number":
        return schema.get("minimum", 0.0)
    if t == "boolean":
        return True
    if t == "string":
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if fmt == "email":
            return "example@example.com"
        enm = schema.get("enum")
        if enm:
            return enm[0]
        return schema.get("minLength", 0) * "a" or "example"
    if t == "array":
        items = schema.get("items", {})
        return [_example_for_schema(items if isinstance(items, dict) else {})]
    if t == "object":
        props = schema.get("properties") or {}
        req = schema.get("required") or []
        out = {}
        for k, v in props.items():
            if k in req:
                out[k] = _example_for_schema(v if isinstance(v, dict) else {})
        return out
    return None


def _build_request(op: dict[str, Any], path_values: dict[str, Any], query: dict[str, Any], headers: dict[str, Any], body: Any) -> dict[str, Any]:
    url = _base_url(op) + _render_path(op["path"], path_values)
    qs = "&".join(f"{k}={v}" for k, v in query.items() if v is not None)
    if qs:
        url += ("?" if "?" not in url else "&") + qs
    method = op["method"].upper()
    request_def = {
        "method": method,
        "url": url,
        "headers": headers,
        "body": None,
    }
    if body is not None:
        request_def["headers"].setdefault("Content-Type", "application/json")
        request_def["body"] = json.dumps(body)
    return request_def


def _positive_assertions(op: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"type": "status_code", "expect": {"in": [200, 201, 202, 204]}}]


def generate_candidates(
    *,
    campaign_id: UUID,
    operation: dict[str, Any],
    operation_id: UUID,
) -> list[dict[str, Any]]:
    """
    Deterministic candidate generation: positive, negative, boundary, schema, minimal workflow.
    Returns a list of {id, kind, request_definition, assertions, provenance}.
    """
    candidates: list[dict[str, Any]] = []

    # Classify parameters by location
    path_params = [p for p in operation.get("parameters", []) if p.get("in") == "path"]
    query_params = [p for p in operation.get("parameters", []) if p.get("in") == "query"]
    header_params = [p for p in operation.get("parameters", []) if p.get("in") == "header"]

    # Build sample values for path/query/header based on schema.
    pv = {p["name"]: _example_for_schema(p.get("schema") or {}) for p in path_params}
    qv = {p["name"]: _example_for_schema(p.get("schema") or {}) for p in query_params if p.get("required")}
    hv = {p["name"]: str(_example_for_schema(p.get("schema") or {})) for p in header_params if p.get("required")}

    # --- Positive (happy path)
    body_example = None
    rb = operation.get("request_body") or {}
    if rb and rb.get("schema"):
        body_example = _example_for_schema(rb.get("schema") or {})
    pos_req = _build_request(operation, pv, qv, dict(hv), body_example)
    cid = _stable_id(campaign_id, f"pos|{operation['method']}|{operation['path']}")
    candidates.append(
        {
            "id": cid,
            "kind": "positive",
            "request_definition": pos_req,
            "assertions": _positive_assertions(operation),
            "provenance": {"source": "deterministic.positive", "operation_id": str(operation_id)},
        }
    )

    # --- Negative: missing required path param, expect 4xx
    if path_params:
        bad_pv = dict(pv)
        first = path_params[0]["name"]
        bad_pv[first] = ""
        req = _build_request(operation, bad_pv, dict(qv), dict(hv), body_example)
        cid = _stable_id(campaign_id, f"neg|missing-path|{first}")
        candidates.append(
            {
                "id": cid,
                "kind": "negative",
                "request_definition": req,
                "assertions": [{"type": "status_code", "expect": {"in": list(range(400, 500))}}],
                "provenance": {"source": "deterministic.negative.missing_path", "param": first},
            }
        )

    # --- Negative: missing required query param
    req_q = [p for p in query_params if p.get("required")]
    if req_q:
        bad_qv = dict(qv)
        first = req_q[0]["name"]
        bad_qv.pop(first, None)
        req = _build_request(operation, pv, bad_qv, dict(hv), body_example)
        cid = _stable_id(campaign_id, f"neg|missing-query|{first}")
        candidates.append(
            {
                "id": cid,
                "kind": "negative",
                "request_definition": req,
                "assertions": [{"type": "status_code", "expect": {"in": list(range(400, 500))}}],
                "provenance": {"source": "deterministic.negative.missing_query", "param": first},
            }
        )

    # --- Negative: wrong type (integer → string)
    int_query = [p for p in query_params if (p.get("schema") or {}).get("type") == "integer"]
    if int_query:
        bad_qv = dict(qv)
        first = int_query[0]["name"]
        bad_qv[first] = "not-an-int"
        req = _build_request(operation, pv, bad_qv, dict(hv), body_example)
        cid = _stable_id(campaign_id, f"neg|type-query|{first}")
        candidates.append(
            {
                "id": cid,
                "kind": "negative",
                "request_definition": req,
                "assertions": [{"type": "status_code", "expect": {"in": list(range(400, 500))}}],
                "provenance": {"source": "deterministic.negative.type_mismatch", "param": first},
            }
        )

    # --- Boundary: very long string query param / body string at maxLength
    str_query = [p for p in query_params if (p.get("schema") or {}).get("type") == "string"]
    if str_query:
        first = str_query[0]["name"]
        schema = str_query[0].get("schema") or {}
        max_len = schema.get("maxLength", 2000)
        long_val = "a" * (max_len + 1)
        bad_qv = dict(qv)
        bad_qv[first] = long_val
        req = _build_request(operation, pv, bad_qv, dict(hv), body_example)
        cid = _stable_id(campaign_id, f"boundary|long-query|{first}")
        candidates.append(
            {
                "id": cid,
                "kind": "boundary",
                "request_definition": req,
                "assertions": [{"type": "status_code", "expect": {"in": list(range(400, 500))}}],
                "provenance": {"source": "deterministic.boundary.long_string", "param": first, "length": len(long_val)},
            }
        )

    # --- Schema: send empty JSON body when body required
    if rb and rb.get("required"):
        req = _build_request(operation, pv, qv, dict(hv), {} if body_example is not None else None)
        cid = _stable_id(campaign_id, "schema|empty-body")
        candidates.append(
            {
                "id": cid,
                "kind": "schema",
                "request_definition": req,
                "assertions": [{"type": "status_code", "expect": {"in": list(range(400, 500))}}],
                "provenance": {"source": "deterministic.schema.empty_body"},
            }
        )

    # --- Workflow: method not allowed (swap GET/POST when applicable) -> 405
    if operation["method"] in {"GET", "POST", "PUT", "DELETE"}:
        wrong_method = "POST" if operation["method"] == "GET" else "GET"
        req_def = dict(pos_req)
        req_def["method"] = wrong_method
        req_def["body"] = None if wrong_method == "GET" else req_def.get("body")
        cid = _stable_id(campaign_id, f"workflow|method-swap|{wrong_method}")
        candidates.append(
            {
                "id": cid,
                "kind": "workflow",
                "request_definition": req_def,
                "assertions": [{"type": "status_code", "expect": {"in": [405, 404]}}],
                "provenance": {"source": "deterministic.workflow.method_swap"},
            }
        )

    # Validate and dedupe candidates before returning.
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for c in candidates:
        validate_candidate(c)
        if c["id"] in seen_ids:
            continue
        seen_ids.add(c["id"])
        out.append(c)
    return out
