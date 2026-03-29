from __future__ import annotations

from typing import Any, Mapping


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _as_text(item)
        if text:
            out.append(text)
    return out


def _ui_badge(visible_state: str) -> str:
    mapping = {
        "UNDERSTOOD": "understood",
        "NEEDS_ONE_OR_TWO_DETAILS": "need-details",
        "EXECUTING": "executing",
        "WAITING_FOR_DECISION": "waiting-decision",
        "BLOCKED_NEEDS_INPUT": "blocked",
        "DONE": "done",
    }
    return mapping.get(visible_state, "understood")


def _reply_style(visible_state: str) -> str:
    if visible_state == "DONE":
        return "delivery"
    if visible_state in {"WAITING_FOR_DECISION", "BLOCKED_NEEDS_INPUT"}:
        return "decision_or_blocker"
    if visible_state == "EXECUTING":
        return "progress"
    return "intake"


def _stage_to_frontend(stage: str, visible_state: str) -> str:
    stage_upper = _as_text(stage).upper()
    if visible_state == "DONE":
        return "done"
    if visible_state == "WAITING_FOR_DECISION":
        return "decision_needed"
    if visible_state == "BLOCKED_NEEDS_INPUT":
        return "advance_blocked"
    if stage_upper in {"EXECUTING", "VERIFYING"}:
        return "executing"
    if stage_upper in {"INTAKE", "PLANNING", "NEW"}:
        return "analysis"
    if stage_upper == "FAILED":
        return "advance_blocked"
    return "analysis"


def _status_to_frontend(stage: str, verify_result: str) -> str:
    stage_upper = _as_text(stage).upper()
    verify = _as_text(verify_result).upper()
    if stage_upper == "DONE" and verify == "PASS":
        return "pass"
    if stage_upper in {"EXECUTING", "VERIFYING"}:
        return "running"
    if stage_upper == "WAITING_DECISION":
        return "blocked"
    if stage_upper in {"BLOCKED", "FAILED"}:
        return "blocked"
    return "running"


def build_render_state(current_state: Mapping[str, Any] | None) -> dict[str, Any]:
    current = current_state if isinstance(current_state, Mapping) else {}
    visible_state = _as_text(current.get("visible_state")) or "UNDERSTOOD"
    blocker = _as_text(current.get("current_blocker")) or "none"
    blocking_question = _as_text(current.get("blocking_question"))
    followups: list[str] = []
    if visible_state in {"WAITING_FOR_DECISION", "BLOCKED_NEEDS_INPUT"} and blocking_question:
        followups.append(blocking_question)
    elif visible_state == "NEEDS_ONE_OR_TWO_DETAILS":
        missing_fields = _as_list(current.get("missing_fields"))
        if missing_fields:
            followups.append(f"请补充：{missing_fields[0]}")

    progress_rows: list[str] = []
    stage = _as_text(current.get("authoritative_stage"))
    if stage:
        progress_rows.append(f"authoritative_stage={stage}")
    confirmed = _as_list(current.get("last_confirmed_items"))
    if confirmed:
        progress_rows.append("confirmed=" + " / ".join(confirmed[:3]))
    if blocker and blocker.lower() != "none":
        progress_rows.append(f"blocker={blocker}")
    next_action = _as_text(current.get("next_action"))
    if next_action:
        progress_rows.append(f"next={next_action}")

    decision_cards: list[dict[str, str]] = []
    if followups:
        decision_cards.append(
            {
                "title": "需要你确认",
                "question": followups[0],
            }
        )

    return {
        "task_id": _as_text(current.get("task_id")),
        "ui_badge": _ui_badge(visible_state),
        "reply_style": _reply_style(visible_state),
        "followup_questions": followups[:2],
        "decision_cards": decision_cards[:2],
        "visible_state": visible_state,
        "progress_summary": "; ".join(progress_rows),
        "proof_refs": _as_list(current.get("proof_refs"))[:4],
    }


def to_frontend_binding(
    current_state: Mapping[str, Any] | None,
    render_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    current = current_state if isinstance(current_state, Mapping) else {}
    render = render_state if isinstance(render_state, Mapping) else {}
    if not current:
        return {}

    visible_state = _as_text(render.get("visible_state")) or _as_text(current.get("visible_state")) or "UNDERSTOOD"
    authoritative_stage = _as_text(current.get("authoritative_stage")).upper() or "NEW"
    verify_result = _as_text(current.get("verify_result")).upper()
    blocker = _as_text(current.get("current_blocker")) or "none"
    blocking_question = _as_text(current.get("blocking_question"))
    next_action = _as_text(current.get("next_action"))
    progress_binding = {
        "current_task_goal": _as_text(current.get("current_task_goal")),
        "current_phase": authoritative_stage.title(),
        "last_confirmed_items": _as_list(current.get("last_confirmed_items"))[:3],
        "current_blocker": blocker,
        "message_purpose": "delivery" if visible_state == "DONE" else "progress",
        "question_needed": "yes" if visible_state in {"WAITING_FOR_DECISION", "BLOCKED_NEEDS_INPUT"} and blocking_question else "no",
        "next_action": next_action,
        "blocking_question": blocking_question,
        "proof_refs": _as_list(current.get("proof_refs"))[:4],
    }
    backend_state = {
        "stage": _stage_to_frontend(authoritative_stage, visible_state),
        "run_status": _status_to_frontend(authoritative_stage, verify_result),
        "verify_result": verify_result,
        "waiting_for_decision": visible_state == "WAITING_FOR_DECISION",
        "decisions_count": 1 if visible_state == "WAITING_FOR_DECISION" and blocking_question else 0,
        "blocked_needs_input": visible_state == "BLOCKED_NEEDS_INPUT",
        "needs_input": visible_state in {"WAITING_FOR_DECISION", "BLOCKED_NEEDS_INPUT"},
        "has_actionable_goal": bool(_as_text(current.get("current_task_goal"))),
        "first_pass_understood": bool(_as_text(current.get("current_task_goal"))),
        "progress_binding": progress_binding,
    }
    return {
        "backend_state": backend_state,
        "visible_state": visible_state,
        "followup_questions": _as_list(render.get("followup_questions"))[:2],
        "task_summary": _as_text(current.get("current_task_goal")),
    }

