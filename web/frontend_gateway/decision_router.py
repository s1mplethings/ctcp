from __future__ import annotations

from typing import Any, Mapping


def pick_primary_decision(decisions_doc: Mapping[str, Any]) -> dict[str, Any] | None:
    rows = decisions_doc.get("decisions", [])
    if not isinstance(rows, list):
        return None
    normalized: list[dict[str, Any]] = [x for x in rows if isinstance(x, dict)]
    if not normalized:
        return None

    priorities = {
        "plan_signed": 0,
        "plan_draft": 1,
        "file_request": 2,
        "review_contract": 3,
        "review_cost": 4,
        "fix_patch": 5,
        "make_patch": 6,
        "reply": 7,
        "question": 8,
    }

    def _rank(row: Mapping[str, Any]) -> tuple[int, str]:
        action = str(row.get("action", "")).strip().lower()
        decision_id = str(row.get("decision_id", "")).strip()
        return (priorities.get(action, 50), decision_id)

    normalized.sort(key=_rank)
    return normalized[0]


def render_decision_question(decision: Mapping[str, Any]) -> str:
    kind = str(decision.get("kind", "")).strip().lower()
    action = str(decision.get("action", "")).strip().lower()
    reason = str(decision.get("reason", "")).strip()
    question_hint = str(decision.get("question_hint", "")).strip()
    target = str(decision.get("target_path", "")).strip()

    if kind == "questions_md":
        return question_hint or reason or "I need one key decision from you before I continue."

    if action == "file_request":
        return (
            "CTCP needs a concrete context request before continuing. "
            "Please tell me which files or modules I should prioritize first."
        )
    if action in {"plan_draft", "plan_signed"}:
        return (
            "CTCP is waiting on planning approval details. "
            "Should I continue with the current plan scope, or adjust scope before execution?"
        )
    if action in {"review_contract", "review_cost"}:
        return (
            "A review decision is pending. "
            "Please confirm whether we should approve this stage or block it with required fixes."
        )
    if action in {"fix_patch", "make_patch"}:
        return (
            "CTCP needs the next patch decision. "
            "Please provide the exact fix direction you want applied for this step."
        )
    if question_hint:
        return question_hint
    if reason:
        return f"CTCP needs your decision to continue: {reason}"
    if target:
        return f"CTCP is waiting for your decision to fill `{target}`."
    return "CTCP needs one decision from you before it can continue."


def build_decision_submission(decision: Mapping[str, Any], user_reply: str) -> dict[str, Any]:
    return {
        "decision_id": str(decision.get("decision_id", "")).strip(),
        "prompt_path": str(decision.get("prompt_path", "")).strip(),
        "target_path": str(decision.get("target_path", "")).strip(),
        "content": str(user_reply or "").strip(),
    }
