from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Mapping

AUTHORITATIVE_STAGES: tuple[str, ...] = (
    "NEW",
    "INTAKE",
    "PLANNING",
    "WAITING_DECISION",
    "EXECUTING",
    "VERIFYING",
    "BLOCKED",
    "DONE",
    "FAILED",
)

EVENT_TYPES: tuple[str, ...] = (
    "user_message",
    "conversation_mode_detected",
    "user_decision_recorded",
    "authoritative_stage_changed",
    "blocker_changed",
    "next_action_set",
    "verification_result_recorded",
    "runtime_progress_recorded",
    "render_state_refreshed",
)

_FRONTEND_WRITABLE_KEYS = {
    "text",
    "message_id",
    "conversation_mode_guess",
    "user_decision",
    "clarification_answer",
    "ui_feedback",
    "known_facts",
    "missing_fields",
    "current_task_goal",
}

_RUNTIME_WRITABLE_KEYS = {
    "authoritative_stage",
    "execution_status",
    "current_blocker",
    "blocking_question",
    "next_action",
    "proof_refs",
    "verify_result",
    "last_confirmed_items",
    "current_task_goal",
    "known_facts",
    "missing_fields",
    "conversation_mode",
    "verification_events",
    "failure_reason",
    "evidence_paths",
    "visible_state",
    "ui_badge",
}

_VERIFIER_WRITABLE_KEYS = {
    "verification_events",
    "failure_reason",
    "evidence_paths",
    "verify_result",
    "proof_refs",
}


@dataclass(frozen=True)
class EventSpec:
    roles: tuple[str, ...]
    required_any_of: tuple[str, ...] = ()


_EVENT_SPECS: dict[str, EventSpec] = {
    "user_message": EventSpec(("frontend", "runtime"), ("text",)),
    "conversation_mode_detected": EventSpec(("frontend", "runtime"), ("conversation_mode_guess",)),
    "user_decision_recorded": EventSpec(("frontend", "runtime"), ("user_decision", "clarification_answer")),
    "authoritative_stage_changed": EventSpec(("runtime",), ("authoritative_stage",)),
    "blocker_changed": EventSpec(("runtime",), ("current_blocker", "blocking_question")),
    "next_action_set": EventSpec(("runtime",), ("next_action",)),
    "verification_result_recorded": EventSpec(("runtime", "verifier"), ("verify_result",)),
    "runtime_progress_recorded": EventSpec(("runtime",), ()),
    "render_state_refreshed": EventSpec(("runtime",), ("visible_state",)),
}


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _source_role(source: str) -> str:
    low = str(source or "").strip().lower()
    if not low:
        return "unknown"
    if any(low.startswith(prefix) for prefix in ("frontend", "frontdesk")):
        return "frontend"
    if any(low.startswith(prefix) for prefix in ("runtime", "orchestrator", "support_bot", "bridge")):
        return "runtime"
    if low.startswith("verifier"):
        return "verifier"
    if any(low.startswith(prefix) for prefix in ("ui_renderer", "support_shell", "renderer")):
        return "ui_readonly"
    return "unknown"


def _validate_payload_permissions(*, role: str, payload: Mapping[str, Any]) -> None:
    keys = set(payload.keys())
    if role == "frontend":
        invalid = sorted(keys - _FRONTEND_WRITABLE_KEYS)
        if invalid:
            raise PermissionError(f"frontend/frontdesk payload contains non-writable keys: {invalid}")
        return
    if role == "runtime":
        invalid = sorted(keys - _RUNTIME_WRITABLE_KEYS)
        if invalid:
            raise PermissionError(f"runtime/orchestrator payload contains non-writable keys: {invalid}")
        return
    if role == "verifier":
        invalid = sorted(keys - _VERIFIER_WRITABLE_KEYS)
        if invalid:
            raise PermissionError(f"verifier payload contains non-writable keys: {invalid}")
        return
    if role == "ui_readonly":
        raise PermissionError("ui renderer/support shell is read-only for shared state events")
    raise PermissionError(f"unknown source role: {role}")


def _normalize_stage(payload: dict[str, Any]) -> None:
    stage = str(payload.get("authoritative_stage", "")).strip().upper()
    if not stage:
        return
    if stage not in AUTHORITATIVE_STAGES:
        raise ValueError(f"invalid authoritative_stage: {stage}")
    payload["authoritative_stage"] = stage


def _normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    out = {str(k): v for k, v in dict(payload).items()}
    _normalize_stage(out)
    return out


def build_event(
    *,
    task_id: str,
    event_type: str,
    source: str,
    payload: Mapping[str, Any] | None = None,
    ts: str = "",
) -> dict[str, Any]:
    tid = str(task_id or "").strip()
    etype = str(event_type or "").strip()
    src = str(source or "").strip()
    body = _normalize_payload(payload if isinstance(payload, Mapping) else {})
    timestamp = str(ts or "").strip() or now_utc_iso()

    if not tid:
        raise ValueError("task_id is required")
    if not etype:
        raise ValueError("event_type is required")
    if etype not in EVENT_TYPES:
        raise ValueError(f"unsupported event type: {etype}")
    if not src:
        raise ValueError("source is required")

    role = _source_role(src)
    spec = _EVENT_SPECS.get(etype)
    if spec is None:
        raise ValueError(f"event spec missing: {etype}")
    if role not in spec.roles:
        raise PermissionError(f"source role '{role}' cannot emit event '{etype}'")
    _validate_payload_permissions(role=role, payload=body)
    if spec.required_any_of and not any(str(body.get(key, "")).strip() for key in spec.required_any_of):
        raise ValueError(f"event '{etype}' requires one of payload keys: {spec.required_any_of}")

    return {
        "ts": timestamp,
        "task_id": tid,
        "type": etype,
        "source": src,
        "payload": body,
    }
