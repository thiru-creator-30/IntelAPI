from __future__ import annotations

import json
from typing import Any

import yaml

from app.core.errors import AppError, ErrorCode
from app.core.config import get_settings


MAX_SPEC_BYTES = 2 * 1024 * 1024  # hard cap before parser (also enforced at fetch time)


class SpecParseError(AppError):
    def __init__(self, reason: str) -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, f"Invalid OpenAPI document: {reason}", details={"reason": reason})


def parse_spec(raw: bytes, *, max_bytes: int | None = None) -> dict[str, Any]:
    cap = max_bytes or get_settings().outbound_spec_max_bytes
    if len(raw) > cap:
        raise SpecParseError(f"spec exceeds size cap ({len(raw)} > {cap})")
    text = raw.decode("utf-8", errors="strict")
    # Try JSON first, then YAML.
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SpecParseError(f"not valid JSON or YAML: {exc}") from exc
    if not isinstance(doc, dict):
        raise SpecParseError("root must be an object")
    return validate_openapi3(doc)


def validate_openapi3(doc: dict[str, Any]) -> dict[str, Any]:
    openapi = doc.get("openapi")
    if openapi is None:
        swagger = doc.get("swagger")
        if swagger and str(swagger).startswith("2"):
            raise SpecParseError("Swagger 2.0 is not supported in MVP; only OpenAPI 3.x")
        raise SpecParseError("missing 'openapi' version")
    if not str(openapi).startswith("3."):
        raise SpecParseError(f"unsupported OpenAPI version: {openapi}")
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        raise SpecParseError("missing or invalid 'paths' object")
    info = doc.get("info")
    if not isinstance(info, dict):
        raise SpecParseError("missing 'info' object")
    # Reject remote $ref anywhere (defense in depth; parser must never fetch).
    _walk_for_remote_refs(doc, path="$")
    return doc


def _walk_for_remote_refs(node: Any, path: str) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                if "://" in v or v.startswith("//"):
                    raise SpecParseError(f"remote $ref not allowed at {path}")
                if v.startswith("#") is False and "/" in v:
                    # Filename $ref like ./other.yaml
                    raise SpecParseError(f"external $ref not allowed at {path}")
            _walk_for_remote_refs(v, path + "." + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_for_remote_refs(v, path + f"[{i}]")
