from __future__ import annotations

from typing import Any


def score_next_tests(prior_results: list[dict[str, Any]], candidates: list[dict[str, Any]], budget_remaining: int) -> list[dict[str, Any]]:
    """
    Deterministic priority ordering:
      1. candidates from operations with no prior executions first
      2. then candidates from operations with failures (schema/status) first
      3. then by kind priority: negative > boundary > schema > workflow > positive
    Returns the top `budget_remaining` candidates with rationale.
    """
    kind_priority = {"negative": 0, "boundary": 1, "schema": 2, "workflow": 3, "positive": 4}

    executed_candidate_ids = {r.get("test_case_id") for r in prior_results if r.get("test_case_id")}
    failing_ops = {r.get("operation_id") for r in prior_results if r.get("outcome") == "assertion_failed"}

    scored: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []
    for c in candidates:
        if c.get("id") in executed_candidate_ids:
            continue
        op_id = (c.get("provenance") or {}).get("operation_id")
        no_prior = 0 if op_id and op_id not in {r.get("operation_id") for r in prior_results} else 1
        failing = 0 if op_id in failing_ops else 1
        kp = kind_priority.get(c.get("kind"), 9)
        rationale = []
        if no_prior == 0:
            rationale.append("new operation with no prior coverage")
        if failing == 0:
            rationale.append("operation has prior failures")
        rationale.append(f"kind={c.get('kind')}")
        scored.append(((no_prior, failing, kp, c.get("id", "")), {**c, "rationale": "; ".join(rationale)}))

    scored.sort(key=lambda x: x[0])
    return [c for _, c in scored[:max(0, budget_remaining)]]
