from __future__ import annotations

from typing import Any


def classify_from_execution(execution: dict[str, Any], assertion_results: list[dict[str, Any]], operation: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Deterministic evidence-based classification.

    Returns list of candidate finding payloads (dicts). Each finding links to evidence.
    No automatic vulnerability claims: categories are observations like
      - status_mismatch
      - latency_threshold_exceeded
      - schema_mismatch
      - header_mismatch
    Severity starts at info/low based on assertion class.
    """
    findings: list[dict[str, Any]] = []
    for ar in assertion_results:
        if ar.get("passed"):
            continue
        atype = ar.get("assertion_type")
        if atype == "status_code":
            cat = "status_mismatch"
            sev = "low"
        elif atype == "latency_ms":
            cat = "latency_threshold_exceeded"
            sev = "info"
        elif atype == "response_header":
            cat = "header_mismatch"
            sev = "info"
        elif atype == "json_path_value" or atype == "response_schema":
            cat = "schema_mismatch"
            sev = "low"
        else:
            cat = "assertion_failed"
            sev = "info"
        findings.append(
            {
                "category": cat,
                "machine_severity": sev,
                "title": f"{cat} on {execution.get('method')} {execution.get('url')}",
                "summary": ar.get("message") or cat,
                "evidence_refs": [execution.get("id"), ar.get("id")],
                "assertion": ar,
            }
        )
    return findings
