from __future__ import annotations

from typing import Any

from app.api_understanding.parser import SpecParseError


HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _resolve_ref(doc: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise SpecParseError(f"cannot resolve non-local $ref: {ref}")
    parts = ref[2:].split("/")
    cur: Any = doc
    for p in parts:
        p = p.replace("~1", "/").replace("~0", "~")
        if not isinstance(cur, dict) or p not in cur:
            raise SpecParseError(f"unresolvable $ref: {ref}")
        cur = cur[p]
    return cur


def _resolve(doc: dict[str, Any], node: Any) -> Any:
    if isinstance(node, dict) and "$ref" in node and isinstance(node["$ref"], str):
        return _resolve(doc, _resolve_ref(doc, node["$ref"]))
    return node


def _safe_resolve(doc: dict[str, Any], node: Any, seen: set[str] | None = None) -> Any:
    seen = seen or set()
    if isinstance(node, dict) and "$ref" in node and isinstance(node["$ref"], str):
        ref = node["$ref"]
        if ref in seen:
            return {"$circular": ref}
        seen = seen | {ref}
        return _safe_resolve(doc, _resolve_ref(doc, ref), seen)
    return node


def normalize_operations(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return a deterministic, flattened list of normalized operations:
    {id, method, path, operation_id, summary, parameters, request_body, responses, tags}
    """
    base_path = ""
    servers = doc.get("servers")
    if isinstance(servers, list) and servers and isinstance(servers[0], dict):
        base_path = servers[0].get("url", "") or ""

    ops: list[dict[str, Any]] = []
    paths = doc.get("paths") or {}
    for path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        path_item = _safe_resolve(doc, path_item)
        common_params = path_item.get("parameters") or []
        for method in sorted(HTTP_METHODS):
            op = path_item.get(method)
            if op is None:
                continue
            op = _safe_resolve(doc, op)
            op_params = list(common_params) + list(op.get("parameters") or [])
            params = []
            for p in op_params:
                p = _safe_resolve(doc, p)
                if not isinstance(p, dict):
                    continue
                sch = _safe_resolve(doc, p.get("schema", {}))
                params.append(
                    {
                        "name": p.get("name"),
                        "in": p.get("in"),
                        "required": bool(p.get("required", False)),
                        "schema": sch if isinstance(sch, dict) else {},
                        "description": p.get("description"),
                    }
                )
            request_body = _safe_resolve(doc, op.get("requestBody")) or None
            rb_normalized: dict[str, Any] | None = None
            if request_body:
                content = request_body.get("content") or {}
                # Prefer application/json, else first
                body_schema = None
                body_ct = None
                if "application/json" in content:
                    body_ct = "application/json"
                    body_schema = _safe_resolve(doc, content["application/json"].get("schema"))
                elif content:
                    body_ct = next(iter(content))
                    body_schema = _safe_resolve(doc, content[body_ct].get("schema"))
                rb_normalized = {
                    "required": bool(request_body.get("required", False)),
                    "content_type": body_ct,
                    "schema": body_schema if isinstance(body_schema, dict) else {},
                }
            responses = {}
            for code, resp in sorted((op.get("responses") or {}).items()):
                resp = _safe_resolve(doc, resp)
                if not isinstance(resp, dict):
                    continue
                content = resp.get("content") or {}
                resp_schema = None
                if "application/json" in content:
                    resp_schema = _safe_resolve(doc, content["application/json"].get("schema"))
                responses[str(code)] = {
                    "description": resp.get("description"),
                    "schema": resp_schema if isinstance(resp_schema, dict) else {},
                }
            operation_id = op.get("operationId") or f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
            ops.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation_id,
                    "summary": op.get("summary") or op.get("description") or None,
                    "tags": op.get("tags") or [],
                    "parameters": params,
                    "request_body": rb_normalized,
                    "responses": responses,
                    "base_url": base_path,
                }
            )
    return ops
