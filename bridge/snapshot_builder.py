from __future__ import annotations

from typing import Any, Mapping

from .event_append import AUTHORITATIVE_STAGES

VISIBLE_STATES: tuple[str, ...] = (
    "UNDERSTOOD",
    "NEEDS_ONE_OR_TWO_DETAILS",
    "EXECUTING",
    "WAITING_FOR_DECISION",
    "BLOCKED_NEEDS_INPUT",
    "DONE",
)


def _clean_text(value: Any, *, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _clean_dict(values: Any) -> dict[str, str]:
    if not isinstance(values, Mapping):
        return {}
    out: dict[str, str] = {}
    for key, value in values.items():
        k = _clean_text(key)
        v = _clean_text(value)
        if k and v:
            out[k] = v
    return out


def _has_completion_evidence(snapshot: Mapping[str, Any]) -> bool:
    verify = _clean_text(snapshot.get("verify_result")).upper()
    proof_refs = _clean_list(snapshot.get("proof_refs"))
    if verify != "PASS":
        return False
    if not proof_refs:
        return False
    status = _clean_text(snapshot.get("execution_status")).lower()
    stage = _clean_text(snapshot.get("authoritative_stage")).upper()
    if stage == "DONE":
        return True
    return status in {"pass", "done", "completed", "success"}


def collapse_visible_state(snapshot: Mapping[str, Any]) -> str:
    stage = _clean_text(snapshot.get("authoritative_stage"), fallback="NEW").upper()
    if stage not in AUTHORITATIVE_STAGES:
        stage = "NEW"
    missing_fields = _clean_list(snapshot.get("missing_fields"))
    blocker = _clean_text(snapshot.get("current_blocker"), fallback="none").lower()

    if stage == "WAITING_DECISION":
        return "WAITING_FOR_DECISION"
    if stage in {"BLOCKED", "FAILED"}:
        return "BLOCKED_NEEDS_INPUT"
    if stage == "DONE":
        if _has_completion_evidence(snapshot):
            return "DONE"
        return "EXECUTING"
    if _has_completion_evidence(snapshot):
        return "DONE"
    if stage in {"EXECUTING", "VERIFYING"}:
        if blocker not in {"", "none"}:
            return "BLOCKED_NEEDS_INPUT"
        return "EXECUTING"
    if missing_fields:
        return "NEEDS_ONE_OR_TWO_DETAILS"
    if stage in {"NEW", "INTAKE", "PLANNING"}:
        return "UNDERSTOOD"
    return "UNDERSTOOD"


def empty_current_snapshot(task_id: str) -> dict[str, Any]:
    return {
        "task_id": _clean_text(task_id),
        "authoritative_stage": "NEW",
        "execution_status": "",
        "visible_state": "NEEDS_ONE_OR_TWO_DETAILS",
        "conversation_mode": "",
        "current_task_goal": "",
        "known_facts": {},
        "missing_fields": [],
        "last_confirmed_items": [],
        "current_blocker": "none",
        "blocking_question": "",
        "next_action": "",
        "proof_refs": [],
        "verify_result": "",
        "latest_user_message": "",
        "last_user_decision": "",
        "failure_reason": "",
        "verification_events": [],
        "evidence_paths": [],
    }


def _merge_known_fields(snapshot: dict[str, Any], payload: Mapping[str, Any]) -> None:
    known_facts = dict(snapshot.get("known_facts", {}))
    known_facts.update(_clean_dict(payload.get("known_facts")))
    snapshot["known_facts"] = known_facts

    incoming_missing = _clean_list(payload.get("missing_fields"))
    if incoming_missing:
        snapshot["missing_fields"] = incoming_missing


def apply_event(snapshot: dict[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    event_type = _clean_text(event.get("type"))
    payload = event.get("payload", {})
    body = payload if isinstance(payload, Mapping) else {}
    _merge_known_fields(snapshot, body)

    if event_type == "user_message":
        snapshot["latest_user_message"] = _clean_text(body.get("text"))
        goal = _clean_text(body.get("current_task_goal"))
        if goal:
            snapshot["current_task_goal"] = goal
    elif event_type == "conversation_mode_detected":
        snapshot["conversation_mode"] = _clean_text(body.get("conversation_mode_guess") or body.get("conversation_mode"))
    elif event_type == "user_decision_recorded":
        decision = _clean_text(body.get("user_decision") or body.get("clarification_answer"))
        if decision:
            snapshot["last_user_decision"] = decision
        question = _clean_text(body.get("blocking_question"))
        if question:
            snapshot["blocking_question"] = question
    elif event_type == "authoritative_stage_changed":
        stage = _clean_text(body.get("authoritative_stage"), fallback=snapshot.get("authoritative_stage", "NEW")).upper()
        if stage in AUTHORITATIVE_STAGES:
            snapshot["authoritative_stage"] = stage
        status = _clean_text(body.get("execution_status"))
        if status:
            snapshot["execution_status"] = status
    elif event_type == "blocker_changed":
        blocker = _clean_text(body.get("current_blocker"), fallback="none")
        snapshot["current_blocker"] = blocker
        question = _clean_text(body.get("blocking_question"))
        if question:
            snapshot["blocking_question"] = question
    elif event_type == "next_action_set":
        action = _clean_text(body.get("next_action"))
        if action:
            snapshot["next_action"] = action
    elif event_type == "verification_result_recorded":
        verify = _clean_text(body.get("verify_result")).upper()
        if verify:
            snapshot["verify_result"] = verify
        proof_refs = _clean_list(body.get("proof_refs"))
        if proof_refs:
            snapshot["proof_refs"] = proof_refs
        verification_events = _clean_list(body.get("verification_events"))
        if verification_events:
            snapshot["verification_events"] = verification_events
        evidence_paths = _clean_list(body.get("evidence_paths"))
        if evidence_paths:
            snapshot["evidence_paths"] = evidence_paths
        failure_reason = _clean_text(body.get("failure_reason"))
        if failure_reason:
            snapshot["failure_reason"] = failure_reason
    elif event_type == "runtime_progress_recorded":
        goal = _clean_text(body.get("current_task_goal"))
        if goal:
            snapshot["current_task_goal"] = goal
        confirmed = _clean_list(body.get("last_confirmed_items"))
        if confirmed:
            snapshot["last_confirmed_items"] = confirmed
        blocker = _clean_text(body.get("current_blocker"))
        if blocker:
            snapshot["current_blocker"] = blocker
        question = _clean_text(body.get("blocking_question"))
        if question:
            snapshot["blocking_question"] = question
        action = _clean_text(body.get("next_action"))
        if action:
            snapshot["next_action"] = action
        mode = _clean_text(body.get("conversation_mode"))
        if mode:
            snapshot["conversation_mode"] = mode
        proof_refs = _clean_list(body.get("proof_refs"))
        if proof_refs:
            snapshot["proof_refs"] = proof_refs
    return snapshot


def rebuild_current_snapshot(*, task_id: str, events: list[Mapping[str, Any]]) -> dict[str, Any]:
    snapshot = empty_current_snapshot(task_id)
    for event in events:
        snapshot = apply_event(snapshot, event)
    snapshot["authoritative_stage"] = _clean_text(snapshot.get("authoritative_stage"), fallback="NEW").upper()
    if snapshot["authoritative_stage"] not in AUTHORITATIVE_STAGES:
        snapshot["authoritative_stage"] = "NEW"
    snapshot["verify_result"] = _clean_text(snapshot.get("verify_result")).upper()
    snapshot["proof_refs"] = _clean_list(snapshot.get("proof_refs"))
    snapshot["missing_fields"] = _clean_list(snapshot.get("missing_fields"))
    snapshot["last_confirmed_items"] = _clean_list(snapshot.get("last_confirmed_items"))
    snapshot["known_facts"] = _clean_dict(snapshot.get("known_facts"))
    snapshot["visible_state"] = collapse_visible_state(snapshot)
    return snapshot

