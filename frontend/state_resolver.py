from __future__ import annotations

from typing import Any, Mapping, Literal

VisibleState = Literal[
    "UNDERSTOOD",
    "NEEDS_ONE_OR_TWO_DETAILS",
    "EXECUTING",
    "WAITING_FOR_DECISION",
    "BLOCKED_NEEDS_INPUT",
    "DONE",
]

VISIBLE_STATES: tuple[VisibleState, ...] = (
    "UNDERSTOOD",
    "NEEDS_ONE_OR_TWO_DETAILS",
    "EXECUTING",
    "WAITING_FOR_DECISION",
    "BLOCKED_NEEDS_INPUT",
    "DONE",
)


def _as_bool(doc: Mapping[str, Any], key: str) -> bool:
    value = doc.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _as_int(doc: Mapping[str, Any], key: str) -> int:
    value = doc.get(key)
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def _as_str(doc: Mapping[str, Any], key: str) -> str:
    return str(doc.get(key, "")).strip()


def _is_done(doc: Mapping[str, Any]) -> bool:
    run_status = _as_str(doc, "run_status").lower()
    verify_result = _as_str(doc, "verify_result").upper()
    stage = _as_str(doc, "stage").lower()
    if run_status in {"pass", "done", "completed"}:
        return True
    if verify_result == "PASS":
        return True
    if stage in {"done", "completed", "final_report_ready"}:
        return True
    return False


def _is_waiting_for_decision(doc: Mapping[str, Any]) -> bool:
    stage = _as_str(doc, "stage").lower()
    if _as_bool(doc, "waiting_for_decision"):
        return True
    if _as_int(doc, "decisions_count") > 0:
        return True
    if _as_int(doc, "question_count") > 0:
        return True
    if "decision" in stage:
        return True
    return False


def _is_blocked_needs_input(doc: Mapping[str, Any]) -> bool:
    stage = _as_str(doc, "stage").lower()
    run_status = _as_str(doc, "run_status").lower()
    next_step = _as_str(doc, "next_step").lower()
    if _as_bool(doc, "blocked_needs_input"):
        return True
    if run_status in {"blocked"} and _as_bool(doc, "needs_input"):
        return True
    if next_step == "blocked":
        return True
    if "advance_blocked" in stage:
        return True
    if "need_more_info" in stage:
        return True
    if run_status in {"failed", "error"} and _as_bool(doc, "needs_input"):
        return True
    return False


def _is_executing(doc: Mapping[str, Any]) -> bool:
    stage = _as_str(doc, "stage").lower()
    run_status = _as_str(doc, "run_status").lower()
    next_step = _as_str(doc, "next_step").lower()
    if _as_bool(doc, "is_executing"):
        return True
    if run_status in {"running", "in_progress", "working"}:
        return True
    if stage in {"advance_success", "executing", "status_reply"}:
        return True
    if next_step in {"ready_apply", "resolve_find_local", "ready_verify"}:
        return True
    return False


def resolve_visible_state(raw_backend_state: Mapping[str, Any]) -> VisibleState:
    """
    Collapse noisy backend/orchestrator states into one user-visible primary state.

    Priority:
    1) WAITING_FOR_DECISION / BLOCKED_NEEDS_INPUT
    2) DONE
    3) EXECUTING
    4) UNDERSTOOD
    5) NEEDS_ONE_OR_TWO_DETAILS
    """

    data = raw_backend_state if isinstance(raw_backend_state, Mapping) else {}

    if _is_waiting_for_decision(data):
        return "WAITING_FOR_DECISION"
    if _is_blocked_needs_input(data):
        return "BLOCKED_NEEDS_INPUT"
    if _is_done(data):
        return "DONE"
    if _is_executing(data):
        return "EXECUTING"
    if _as_bool(data, "first_pass_understood") or _as_bool(data, "has_actionable_goal"):
        return "UNDERSTOOD"
    return "NEEDS_ONE_OR_TWO_DETAILS"

