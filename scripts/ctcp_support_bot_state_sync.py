#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
from typing import Any

from scripts.ctcp_support_bot_constants import (
    SUPPORT_HISTORY_RAW_TURN_LIMIT,
    SUPPORT_STAGE_EXIT_RULES,
    _FINAL_READY_RUN_STATUSES,
)
from scripts.ctcp_support_bot_io import now_iso
from scripts.ctcp_support_bot_progress import build_progress_binding
from scripts.ctcp_support_bot_reply_utils import detect_lang_hint, sanitize_inline_text
from scripts.ctcp_support_bot_session_state import (
    _state_zone,
    current_project_brief,
    history_layers_state,
    latest_turn_memory,
)
from scripts.ctcp_support_recovery import runtime_phase_to_support_stage as runtime_phase_to_support_stage_impl


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def _host_bool(name: str, *args: Any) -> bool:
    module = _support_bot_host_module()
    candidate = getattr(module, name, None) if module is not None else None
    return bool(candidate(*args)) if callable(candidate) else False


def _append_history_turn(
    session_state: dict[str, Any],
    *,
    role: str,
    text: str,
    source: str,
    conversation_mode: str,
    message_intent: str = "",
    ts: str = "",
) -> None:
    sanitized_text = sanitize_inline_text(text, max_chars=360)
    if not sanitized_text:
        return
    layers = history_layers_state(session_state)
    rows = layers.get("raw_turns", [])
    if not isinstance(rows, list):
        rows = []
    rows.append(
        {
            "ts": sanitize_inline_text(ts or now_iso(), max_chars=40),
            "role": sanitize_inline_text(role, max_chars=16) or "user",
            "source": sanitize_inline_text(source, max_chars=40),
            "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
            "message_intent": sanitize_inline_text(message_intent, max_chars=24),
            "text": sanitized_text,
        }
    )
    layers["raw_turns"] = rows[-SUPPORT_HISTORY_RAW_TURN_LIMIT:]


def _classify_message_intent(
    *,
    user_text: str,
    conversation_mode: str,
    frontdesk_state: dict[str, Any] | None,
    has_active_task: bool,
) -> str:
    mode = sanitize_inline_text(conversation_mode, max_chars=40).upper()
    if mode == "STATUS_QUERY":
        return "status_check"
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return "small_talk"
    interrupt = sanitize_inline_text(str((frontdesk_state or {}).get("interrupt_kind", "")), max_chars=24).lower()
    if interrupt == "clarify":
        return "clarify"
    if interrupt in {"override", "redirect", "sidequest"}:
        return "constraint_update"
    if mode == "PROJECT_INTAKE":
        if has_active_task and _host_bool("should_refresh_project_brief", user_text, mode) and not _host_bool("is_project_execution_followup", user_text):
            return "new_task"
        return "continue" if has_active_task else "new_task"
    if mode in {"PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return "continue" if has_active_task else "new_task"
    return "continue"


def _project_runtime_state(project_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    runtime_state = project_context.get("runtime_state", {})
    return runtime_state if isinstance(runtime_state, dict) else {}


def _runtime_phase_to_support_stage(phase: str) -> str:
    return runtime_phase_to_support_stage_impl(phase)


def _derive_active_stage(
    *,
    conversation_mode: str,
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    delivery_state: dict[str, Any] | None,
    provider_result: dict[str, Any] | None,
) -> tuple[str, str]:
    mode = sanitize_inline_text(conversation_mode, max_chars=40).upper()
    state_name = sanitize_inline_text(str((frontdesk_state or {}).get("state", "")), max_chars=40).lower()
    runtime_state = _project_runtime_state(project_context)
    render_snapshot = {}
    if isinstance(project_context, dict):
        render_snapshot = project_context.get("render_snapshot", {}) or project_context.get("render_state_snapshot", {})
    if not isinstance(render_snapshot, dict):
        render_snapshot = {}
    runtime_phase = sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40).upper()
    status = (project_context or {}).get("status", {}) if isinstance(project_context, dict) else {}
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    run_status = sanitize_inline_text(
        str(runtime_state.get("run_status", "")).strip() or str(status.get("run_status", "")).strip(),
        max_chars=40,
    ).lower()
    verify_result = sanitize_inline_text(
        str(runtime_state.get("verify_result", "")).strip() or str(status.get("verify_result", "")).strip(),
        max_chars=20,
    ).upper()
    gate_state = sanitize_inline_text(str(gate.get("state", "")), max_chars=40).lower()
    gate_owner = sanitize_inline_text(str(gate.get("owner", "")), max_chars=80).lower()
    gate_reason = sanitize_inline_text(str(gate.get("reason", "")), max_chars=220).lower()
    visible_state = sanitize_inline_text(str(render_snapshot.get("visible_state", "")), max_chars=40).upper()
    decision_cards = render_snapshot.get("decision_cards", [])
    if not isinstance(decision_cards, list):
        decision_cards = []
    needs_decision = bool(runtime_state.get("needs_user_decision", False)) or bool(decision_cards) or visible_state == "WAITING_FOR_DECISION"
    if not needs_decision:
        needs_decision = bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0
    provider_status = sanitize_inline_text(str((provider_result or {}).get("status", "")), max_chars=32).lower()
    provider_error = provider_status in {"exec_failed", "failed", "error"}
    runtime_error = runtime_state.get("error", {})
    if not isinstance(runtime_error, dict):
        runtime_error = {}
    run_error = bool(runtime_error.get("has_error", False)) or run_status in {"fail", "failed", "error", "aborted"} or gate_state in {"error", "failed"}
    final_ready = verify_result == "PASS" and run_status in _FINAL_READY_RUN_STATUSES and not needs_decision
    delivery_ready = bool(
        (delivery_state or {}).get("package_ready", False)
        or (delivery_state or {}).get("screenshot_ready", False)
        or (delivery_state or {}).get("video_ready", False)
    )
    runtime_stage = _runtime_phase_to_support_stage(runtime_phase)
    if runtime_stage in {"RETRYING", "RECOVERY_NEEDED", "EXEC_FAILED", "BLOCKED_HARD"}:
        return runtime_stage, f"canonical_phase:{runtime_phase.lower()}"
    if provider_error or run_error or bool((project_context or {}).get("error")):
        return "RECOVER", "runtime_or_provider_failure"
    if runtime_stage:
        if runtime_stage == "DELIVER" and (not delivery_ready) and state_name != "showing_result":
            return "FINALIZE", f"canonical_phase:{runtime_phase.lower()}_pending_delivery"
        return runtime_stage, f"canonical_phase:{runtime_phase.lower()}"
    if needs_decision or state_name == "showing_decision":
        return "WAIT_USER_DECISION", "decision_required"
    if final_ready and (delivery_ready or state_name == "showing_result"):
        return "DELIVER", "final_ready_for_delivery"
    if final_ready:
        return "FINALIZE", "final_ready_pending_delivery_payload"
    if state_name == "waiting_user_reply":
        return "CLARIFY", "frontdesk_clarify_state"
    if state_name in {"collecting_input", "idle"} or mode in {"PROJECT_INTAKE", "GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return "INTAKE", "intake_or_non_project_turn"
    if state_name == "showing_error":
        return "RECOVER", "frontdesk_error_state"
    if state_name == "showing_progress":
        if gate_state == "blocked" and ("review" in gate_owner or "review" in gate_reason or "verify" in gate_reason):
            return "VERIFY", "gate_blocked_on_review_verify_step"
        return "EXECUTE", "active_execution_state"
    if state_name == "showing_result":
        return "FINALIZE", "result_packaging_state"
    if run_status in {"running", "in_progress", "working"}:
        return "EXECUTE", "run_status_running"
    return "INTAKE", "default_stage"


def _sync_history_preferences_from_style(
    session_state: dict[str, Any],
    *,
    user_text: str,
    frontdesk_state: dict[str, Any] | None,
) -> None:
    layers = history_layers_state(session_state)
    prefs = _state_zone(layers, "user_preferences")
    style_profile = (frontdesk_state or {}).get("user_style_profile", {})
    if isinstance(style_profile, dict):
        for key, max_chars in (("language", 12), ("tone", 40), ("initiative", 24), ("verbosity", 24)):
            value = sanitize_inline_text(str(style_profile.get(key, "")), max_chars=max_chars).lower()
            if value:
                prefs[key] = value
    raw = sanitize_inline_text(user_text, max_chars=280).lower()
    if any(token in raw for token in ("别机械", "不要机械", "not so mechanical", "natural")):
        prefs["avoid_mechanical"] = True
    if any(token in raw for token in ("一次推进到底", "继续推进", "push to delivery", "继续做")):
        prefs["prefer_push_to_delivery"] = True
    if any(token in raw for token in ("少确认", "少问", "ask only when needed", "less proactive")):
        prefs["prefer_less_questions"] = True
    if any(token in raw for token in ("像负责人", "负责人汇报", "owner-style", "manager")):
        prefs["prefer_owner_report_style"] = True


def sync_active_task_truth(
    session_state: dict[str, Any],
    *,
    user_text: str,
    source: str,
    conversation_mode: str,
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    delivery_state: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
    assistant_reply_text: str = "",
    rewrite_latest_user_turn: bool = True,
) -> None:
    previous_goal = sanitize_inline_text(str(session_state.get("active_goal", "")), max_chars=280)
    previous_task_id = sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80)
    previous_run_id = sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80)
    current_goal = sanitize_inline_text(
        str((frontdesk_state or {}).get("current_goal", "")).strip() or current_project_brief(session_state),
        max_chars=280,
    )
    run_id = sanitize_inline_text(
        str(session_state.get("bound_run_id", "")).strip() or str((project_context or {}).get("run_id", "")).strip() or previous_run_id,
        max_chars=80,
    )
    has_active_task = bool(previous_task_id or previous_goal or current_goal or run_id)
    message_intent = _classify_message_intent(
        user_text=user_text,
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        has_active_task=has_active_task,
    )
    stage, stage_reason = _derive_active_stage(
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        delivery_state=delivery_state,
        provider_result=provider_result,
    )
    if assistant_reply_text and stage == "DELIVER":
        stage = "DELIVERED"
        stage_reason = "delivery_reply_emitted"
    binding = build_progress_binding(project_context=project_context, task_summary_hint=current_goal)
    blocker = sanitize_inline_text(str(binding.get("current_blocker", "")).strip() if isinstance(binding, dict) else "", max_chars=220)
    blocker = blocker or sanitize_inline_text(str((frontdesk_state or {}).get("blocked_reason", "")), max_chars=220) or "none"
    next_action = sanitize_inline_text(str(binding.get("next_action", "")).strip() if isinstance(binding, dict) else "", max_chars=220)
    next_action = next_action or sanitize_inline_text(str((frontdesk_state or {}).get("waiting_for", "")), max_chars=220)
    next_action = next_action or "继续按当前主任务推进，并在阶段变化时同步。"
    if message_intent != "new_task":
        current_goal = current_goal or previous_goal
        run_id = run_id or previous_run_id
    active_task_id = run_id or previous_task_id
    if (message_intent == "new_task") and current_goal and not active_task_id:
        digest = hashlib.sha1(current_goal.encode("utf-8", errors="replace")).hexdigest()[:10]
        active_task_id = f"task-{digest}"
    _write_active_task_fields(
        session_state,
        active_task_id=active_task_id,
        run_id=run_id,
        current_goal=current_goal,
        stage=stage,
        stage_reason=stage_reason,
        blocker=blocker,
        next_action=next_action,
        message_intent=message_intent,
    )
    _write_history_layers(
        session_state,
        current_goal=current_goal,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        binding=binding,
        blocker=blocker,
        next_action=next_action,
        active_task_id=active_task_id,
        run_id=run_id,
        stage=stage,
        message_intent=message_intent,
    )
    _sync_history_preferences_from_style(session_state, user_text=user_text, frontdesk_state=frontdesk_state)
    _rewrite_latest_user_turn(session_state, rewrite=rewrite_latest_user_turn, message_intent=message_intent, conversation_mode=conversation_mode)
    if assistant_reply_text:
        _append_history_turn(
            session_state,
            role="assistant",
            text=assistant_reply_text,
            source=source,
            conversation_mode=conversation_mode,
            message_intent=message_intent,
        )


def _write_active_task_fields(
    session_state: dict[str, Any],
    *,
    active_task_id: str,
    run_id: str,
    current_goal: str,
    stage: str,
    stage_reason: str,
    blocker: str,
    next_action: str,
    message_intent: str,
) -> None:
    session_state["active_task_id"] = active_task_id
    session_state["active_run_id"] = run_id
    session_state["active_goal"] = current_goal
    session_state["active_stage"] = stage
    session_state["active_stage_reason"] = stage_reason
    session_state["active_stage_exit_condition"] = SUPPORT_STAGE_EXIT_RULES.get(stage, "")
    session_state["active_blocker"] = blocker
    session_state["active_next_action"] = next_action
    session_state["latest_message_intent"] = message_intent


def _write_history_layers(
    session_state: dict[str, Any],
    *,
    current_goal: str,
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    binding: dict[str, Any],
    blocker: str,
    next_action: str,
    active_task_id: str,
    run_id: str,
    stage: str,
    message_intent: str,
) -> None:
    layers = history_layers_state(session_state)
    working_memory = _state_zone(layers, "working_memory")
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    execution_memory = _state_zone(session_state, "execution_memory")
    completed_items = binding.get("last_confirmed_items", []) if isinstance(binding, dict) else []
    if not isinstance(completed_items, list):
        completed_items = []
    working_memory.update(
        {
            "current_goal": current_goal,
            "current_constraints": sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=280),
            "current_stage": stage,
            "pending_decision": sanitize_inline_text(str((frontdesk_state or {}).get("waiting_for", "")), max_chars=220),
            "completed_results": [sanitize_inline_text(str(x), max_chars=220) for x in completed_items if str(x).strip()][:6],
            "last_failure_reason": sanitize_inline_text(str((project_context or {}).get("error", "")), max_chars=220),
            "next_action": next_action,
            "active_task_id": active_task_id,
            "active_run_id": run_id,
            "active_blocker": blocker,
            "latest_message_intent": message_intent,
        }
    )
    summary = _state_zone(layers, "task_summary")
    confirmed_requirements = [
        sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=220),
        sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=220),
    ]
    summary["task_goal"] = current_goal
    summary["confirmed_requirements"] = [x for x in confirmed_requirements if x][:6]
    summary["completed_steps"] = [sanitize_inline_text(str(x), max_chars=220) for x in completed_items if str(x).strip()][:6]
    summary["pending_steps"] = [next_action] if next_action else []
    summary["current_risks"] = [] if blocker in {"", "none"} else [blocker]
    summary["result_location"] = sanitize_inline_text(str(session_state.get("bound_run_dir", "")), max_chars=260) or run_id
    summary["last_compaction_ts"] = now_iso()


def _rewrite_latest_user_turn(
    session_state: dict[str, Any],
    *,
    rewrite: bool,
    message_intent: str,
    conversation_mode: str,
) -> None:
    rows = history_layers_state(session_state).get("raw_turns", [])
    if not rewrite or not isinstance(rows, list):
        return
    for item in reversed(rows):
        if not isinstance(item, dict):
            continue
        if sanitize_inline_text(str(item.get("role", "")), max_chars=16).lower() != "user":
            continue
        item["message_intent"] = message_intent
        item["conversation_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)
        break


def record_turn_memory(session_state: dict[str, Any], *, user_text: str, source: str, conversation_mode: str) -> None:
    turn_memory = latest_turn_memory(session_state)
    turn_memory["latest_user_turn"] = sanitize_inline_text(user_text, max_chars=280)
    turn_memory["latest_user_turn_ts"] = now_iso()
    turn_memory["latest_conversation_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)
    turn_memory["latest_source"] = sanitize_inline_text(source, max_chars=40)
    session_profile = _state_zone(session_state, "session_profile")
    session_profile["lang_hint"] = detect_lang_hint(user_text)
    session_profile["last_source"] = sanitize_inline_text(source, max_chars=40)
    session_state["latest_conversation_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)
    _append_history_turn(
        session_state,
        role="user",
        text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        message_intent=sanitize_inline_text(str(session_state.get("latest_message_intent", "")), max_chars=24),
    )


__all__ = [
    "_append_history_turn",
    "_classify_message_intent",
    "_project_runtime_state",
    "_runtime_phase_to_support_stage",
    "_derive_active_stage",
    "_sync_history_preferences_from_style",
    "sync_active_task_truth",
    "record_turn_memory",
]
