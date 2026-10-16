from __future__ import annotations

from typing import Any
from uuid import UUID

PROVENANCES = {"DECLARED", "EXTRACTED", "OBSERVED", "INFERRED"}


def make_fact(
    *,
    provenance: str,
    fact_type: str,
    payload: dict[str, Any],
    subject_type: str | None = None,
    subject_id: UUID | None = None,
) -> dict[str, Any]:
    if provenance not in PROVENANCES:
        raise ValueError(f"invalid provenance {provenance}")
    return {
        "provenance": provenance,
        "fact_type": fact_type,
        "payload": payload,
        "subject_type": subject_type,
        "subject_id": str(subject_id) if subject_id else None,
    }


def facts_from_spec(doc: dict[str, Any], spec_id: UUID) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    info = doc.get("info") or {}
    facts.append(make_fact(provenance="DECLARED", fact_type="spec_info", payload=info, subject_type="specification", subject_id=spec_id))
    servers = doc.get("servers") or []
    if servers:
        facts.append(make_fact(provenance="DECLARED", fact_type="spec_servers", payload={"servers": servers}, subject_type="specification", subject_id=spec_id))
    return facts


def facts_from_operation(op: dict[str, Any], op_id: UUID, spec_id: UUID) -> list[dict[str, Any]]:
    return [
        make_fact(
            provenance="EXTRACTED",
            fact_type="operation",
            payload={
                "method": op["method"],
                "path": op["path"],
                "operation_id": op["operation_id"],
                "parameters": op["parameters"],
                "has_request_body": op.get("request_body") is not None,
                "response_codes": list((op.get("responses") or {}).keys()),
            },
            subject_type="operation",
            subject_id=op_id,
        ),
    ]
