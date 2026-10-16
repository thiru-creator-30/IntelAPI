from __future__ import annotations

TERMINAL_STATES = {"completed", "failed", "cancelled"}
ACTIVE_STATES = {"queued", "running"}


def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def can_transition(from_state: str, to_state: str) -> bool:
    if from_state in TERMINAL_STATES:
        return False
    allowed: dict[str, set[str]] = {
        "queued": {"running", "failed", "cancelled"},
        "running": {"completed", "failed", "cancelled"},
    }
    return to_state in allowed.get(from_state, set())
