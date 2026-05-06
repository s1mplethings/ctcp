#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_session_state import (
    _state_zone,
    current_project_brief,
    default_support_session_state,
    frontend_normalize_frontdesk_state,
    frontend_normalize_reply_dedupe_memory,
    sanitize_inline_text,
)

_MERGED_STATE_ZONES = {
    "session_profile",
    "project_memory",
    "project_constraints_memory",
    "execution_memory",
    "turn_memory",
    "history_layers",
    "provider_runtime_buffer",
    "reply_dedupe_memory",
    "notification_state",
    "controller_state",
    "outbound_queue",
    "resume_state",
    "generation_state",
    "latest_support_context",
    "frontdesk_state",
}


def _clean_list(raw: Any, *, max_chars: int, limit: int) -> list[str]:
    if not isinstance(raw, list):
        raw = []
    return [sanitize_inline_text(str(x), max_chars=max_chars) for x in raw if str(x).strip()][:limit]


def _merge_session_doc(state: dict[str, Any], doc: dict[str, Any] | None) -> None:
    if not isinstance(doc, dict):
        return
    for key, value in doc.items():
        if key in _MERGED_STATE_ZONES:
            if isinstance(value, dict):
                _state_zone(state, key).update(value)
            continue
        state[key] = value


def _session_zones(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    zones = {key: _state_zone(state, key) for key in _MERGED_STATE_ZONES if key not in {"frontdesk_state", "latest_support_context"}}
    if not isinstance(state.get("frontdesk_state"), dict):
        state["frontdesk_state"] = {}
    if not isinstance(state.get("latest_support_context"), dict):
        state["latest_support_context"] = {}
    zones["frontdesk_state"] = state["frontdesk_state"]
    zones["latest_support_context"] = state["latest_support_context"]
    return zones


def _normalize_project_turn_memory(state: dict[str, Any], zones: dict[str, dict[str, Any]]) -> None:
    project_memory = zones["project_memory"]
    project_constraints = zones["project_constraints_memory"]
    execution_memory = zones["execution_memory"]
    turn_memory = zones["turn_memory"]
    legacy_summary = sanitize_inline_text(str(state.get("task_summary", "")), max_chars=280)
    if not str(project_memory.get("project_brief", "")).strip() and legacy_summary:
        project_memory["project_brief"] = legacy_summary
    project_memory["project_brief"] = sanitize_inline_text(str(project_memory.get("project_brief", "")), max_chars=280)
    project_memory["last_detail_turn"] = sanitize_inline_text(str(project_memory.get("last_detail_turn", "")), max_chars=280)
    project_memory["last_detail_ts"] = sanitize_inline_text(str(project_memory.get("last_detail_ts", "")), max_chars=40)
    project_constraints["constraint_brief"] = sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=280)
    project_constraints["constraint_ts"] = sanitize_inline_text(str(project_constraints.get("constraint_ts", "")), max_chars=40)
    execution_memory["latest_user_directive"] = sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=280)
    execution_memory["latest_user_directive_ts"] = sanitize_inline_text(str(execution_memory.get("latest_user_directive_ts", "")), max_chars=40)
    turn_memory["latest_user_turn"] = sanitize_inline_text(str(turn_memory.get("latest_user_turn", "")), max_chars=280)
    turn_memory["latest_user_turn_ts"] = sanitize_inline_text(str(turn_memory.get("latest_user_turn_ts", "")), max_chars=40)
    turn_memory["latest_conversation_mode"] = sanitize_inline_text(
        str(turn_memory.get("latest_conversation_mode", state.get("latest_conversation_mode", ""))), max_chars=40
    )
    turn_memory["latest_source"] = sanitize_inline_text(str(turn_memory.get("latest_source", "")), max_chars=40)


def _normalize_raw_turns(history_layers: dict[str, Any]) -> None:
    raw_turns = history_layers.get("raw_turns", [])
    if not isinstance(raw_turns, list):
        raw_turns = []
    normalized: list[dict[str, Any]] = []
    for item in raw_turns[-SUPPORT_HISTORY_RAW_TURN_LIMIT:]:
        if not isinstance(item, dict):
            continue
        text = sanitize_inline_text(str(item.get("text", "")), max_chars=360)
        if not text:
            continue
        normalized.append(
            {
                "ts": sanitize_inline_text(str(item.get("ts", "")), max_chars=40),
                "role": sanitize_inline_text(str(item.get("role", "user")), max_chars=16) or "user",
                "source": sanitize_inline_text(str(item.get("source", "")), max_chars=40),
                "conversation_mode": sanitize_inline_text(str(item.get("conversation_mode", "")), max_chars=40),
                "message_intent": sanitize_inline_text(str(item.get("message_intent", "")), max_chars=24),
                "text": text,
            }
        )
    history_layers["raw_turns"] = normalized


def _normalize_working_memory(history_layers: dict[str, Any]) -> None:
    working = _state_zone(history_layers, "working_memory")
    working["current_goal"] = sanitize_inline_text(str(working.get("current_goal", "")), max_chars=280)
    working["current_constraints"] = sanitize_inline_text(str(working.get("current_constraints", "")), max_chars=280)
    working["current_stage"] = sanitize_inline_text(str(working.get("current_stage", "INTAKE")), max_chars=32)
    if working["current_stage"] not in SUPPORT_ACTIVE_STAGES:
        working["current_stage"] = "INTAKE"
    working["pending_decision"] = sanitize_inline_text(str(working.get("pending_decision", "")), max_chars=220)
    working["completed_results"] = _clean_list(working.get("completed_results", []), max_chars=220, limit=6)
    working["last_failure_reason"] = sanitize_inline_text(str(working.get("last_failure_reason", "")), max_chars=220)
    working["next_action"] = sanitize_inline_text(str(working.get("next_action", "")), max_chars=220)
    working["active_task_id"] = sanitize_inline_text(str(working.get("active_task_id", "")), max_chars=80)
    working["active_run_id"] = sanitize_inline_text(str(working.get("active_run_id", "")), max_chars=80)
    working["active_blocker"] = sanitize_inline_text(str(working.get("active_blocker", "none")), max_chars=220) or "none"
    working["latest_message_intent"] = sanitize_inline_text(str(working.get("latest_message_intent", "continue")), max_chars=24)
    if working["latest_message_intent"] not in SUPPORT_MESSAGE_INTENTS:
        working["latest_message_intent"] = "continue"


def _normalize_history_summary(history_layers: dict[str, Any]) -> None:
    summary = _state_zone(history_layers, "task_summary")
    summary["task_goal"] = sanitize_inline_text(str(summary.get("task_goal", "")), max_chars=280)
    summary["confirmed_requirements"] = _clean_list(summary.get("confirmed_requirements", []), max_chars=220, limit=8)
    summary["completed_steps"] = _clean_list(summary.get("completed_steps", []), max_chars=220, limit=8)
    summary["pending_steps"] = _clean_list(summary.get("pending_steps", []), max_chars=220, limit=8)
    summary["current_risks"] = _clean_list(summary.get("current_risks", []), max_chars=220, limit=6)
    summary["result_location"] = sanitize_inline_text(str(summary.get("result_location", "")), max_chars=260)
    summary["last_compaction_ts"] = sanitize_inline_text(str(summary.get("last_compaction_ts", "")), max_chars=40)


def _normalize_user_preferences(history_layers: dict[str, Any]) -> None:
    prefs = _state_zone(history_layers, "user_preferences")
    prefs["language"] = sanitize_inline_text(str(prefs.get("language", "auto")), max_chars=12) or "auto"
    prefs["tone"] = sanitize_inline_text(str(prefs.get("tone", "task_progressive")), max_chars=40) or "task_progressive"
    prefs["initiative"] = sanitize_inline_text(str(prefs.get("initiative", "balanced")), max_chars=24) or "balanced"
    prefs["verbosity"] = sanitize_inline_text(str(prefs.get("verbosity", "normal")), max_chars=24) or "normal"
    prefs["avoid_mechanical"] = bool(prefs.get("avoid_mechanical", False))
    prefs["prefer_push_to_delivery"] = bool(prefs.get("prefer_push_to_delivery", False))
    prefs["prefer_less_questions"] = bool(prefs.get("prefer_less_questions", False))
    prefs["prefer_owner_report_style"] = bool(prefs.get("prefer_owner_report_style", True))


def _normalize_provider_runtime(provider_runtime: dict[str, Any]) -> None:
    attempted = provider_runtime.get("attempted_providers", [])
    if not isinstance(attempted, list):
        attempted = []
    provider_runtime["preferred_provider"] = sanitize_inline_text(str(provider_runtime.get("preferred_provider", "")), max_chars=40)
    provider_runtime["attempted_providers"] = [sanitize_inline_text(str(item), max_chars=40) for item in attempted if str(item).strip()][-6:]
    provider_runtime["last_provider"] = sanitize_inline_text(str(provider_runtime.get("last_provider", "")), max_chars=40)
    provider_runtime["last_provider_status"] = sanitize_inline_text(str(provider_runtime.get("last_provider_status", "")), max_chars=40)
    provider_runtime["last_provider_reason"] = sanitize_inline_text(str(provider_runtime.get("last_provider_reason", "")), max_chars=220)


def _normalize_notification_state(notification_state: dict[str, Any]) -> None:
    for key, max_chars in {
        "last_progress_hash": 80,
        "last_progress_ts": 40,
        "last_notified_run_id": 80,
        "last_notified_phase": 80,
        "last_auto_advance_ts": 40,
        "last_seen_status_hash": 80,
        "last_sent_message_hash": 80,
        "last_sent_kind": 24,
        "last_decision_prompt_hash": 80,
        "cooldown_until_ts": 40,
    }.items():
        notification_state[key] = sanitize_inline_text(str(notification_state.get(key, "")), max_chars=max_chars)


def _normalize_controller_and_outbound(controller_state: dict[str, Any], outbound_queue: dict[str, Any]) -> None:
    controller_state["current"] = sanitize_inline_text(str(controller_state.get("current", "BOOTSTRAP")), max_chars=40) or "BOOTSTRAP"
    controller_state["last_transition_ts"] = sanitize_inline_text(str(controller_state.get("last_transition_ts", "")), max_chars=40)
    controller_state["last_reason"] = sanitize_inline_text(str(controller_state.get("last_reason", "")), max_chars=220)
    pending_ids = outbound_queue.get("pending_ids", [])
    if not isinstance(pending_ids, list):
        pending_ids = []
    outbound_queue["pending_ids"] = [sanitize_inline_text(str(item), max_chars=120) for item in pending_ids if sanitize_inline_text(str(item), max_chars=120)][-64:]
    jobs = outbound_queue.get("jobs", [])
    if not isinstance(jobs, list):
        jobs = []
    outbound_queue["jobs"] = [_normalize_outbound_job(item) for item in jobs[-32:] if isinstance(item, dict)]


def _normalize_outbound_job(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": sanitize_inline_text(str(item.get("id", "")), max_chars=120),
        "kind": sanitize_inline_text(str(item.get("kind", "")), max_chars=24),
        "run_id": sanitize_inline_text(str(item.get("run_id", "")), max_chars=80),
        "status_hash": sanitize_inline_text(str(item.get("status_hash", "")), max_chars=80),
        "reason": sanitize_inline_text(str(item.get("reason", "")), max_chars=220),
        "message_hash": sanitize_inline_text(str(item.get("message_hash", "")), max_chars=80),
        "decision_prompt": sanitize_inline_text(str(item.get("decision_prompt", "")), max_chars=280),
        "decision_prompt_hash": sanitize_inline_text(str(item.get("decision_prompt_hash", "")), max_chars=80),
        "created_ts": sanitize_inline_text(str(item.get("created_ts", "")), max_chars=40),
    }


def _normalize_resume_state(resume_state: dict[str, Any]) -> None:
    resume_state["last_resume_ts"] = sanitize_inline_text(str(resume_state.get("last_resume_ts", "")), max_chars=40)
    resume_state["last_resume_source_dir"] = sanitize_inline_text(str(resume_state.get("last_resume_source_dir", "")), max_chars=260)
    resume_state["last_resume_source_run_id"] = sanitize_inline_text(str(resume_state.get("last_resume_source_run_id", "")), max_chars=80)
    resume_state["last_resume_brief"] = sanitize_inline_text(str(resume_state.get("last_resume_brief", "")), max_chars=280)
    resume_state["superseded_run_id"] = sanitize_inline_text(str(resume_state.get("superseded_run_id", "")), max_chars=80)


def _normalize_generation_state(generation_state: dict[str, Any]) -> None:
    fields = {
        "current_state": ("T0_PLAN", 32),
        "last_trigger_text": ("", 280),
        "last_trigger_ts": ("", 40),
        "last_mode": ("", 40),
        "last_test_mode": ("", 40),
        "last_pass_fail": ("", 12),
        "last_failure_stage": ("", 40),
        "last_concise_reason": ("", 220),
        "last_command_or_entry": ("", 120),
        "last_out_dir": ("", 320),
        "last_run_dir": ("", 320),
        "last_generated_project_dir": ("", 320),
        "last_report_ts": ("", 40),
        "last_report_path": (SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix(), 220),
    }
    for key, (default, max_chars) in fields.items():
        generation_state[key] = sanitize_inline_text(str(generation_state.get(key, default)), max_chars=max_chars) or default
    state_history = generation_state.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []
    generation_state["state_history"] = [_normalize_generation_history_item(item) for item in state_history[-24:] if isinstance(item, dict)]


def _normalize_generation_history_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": sanitize_inline_text(str(item.get("state", "")), max_chars=32),
        "ts": sanitize_inline_text(str(item.get("ts", "")), max_chars=40),
        "note": sanitize_inline_text(str(item.get("note", "")), max_chars=220),
    }


def _normalize_frontdesk_state(state: dict[str, Any], zones: dict[str, dict[str, Any]]) -> None:
    try:
        state["frontdesk_state"] = frontend_normalize_frontdesk_state(
            zones["frontdesk_state"],
            sanitize_inline_text(str(zones["session_profile"].get("lang_hint", "")), max_chars=12).lower(),
        )
    except Exception:
        state["frontdesk_state"] = zones["frontdesk_state"]


def _normalize_top_level_state(state: dict[str, Any], turn_memory: dict[str, Any]) -> None:
    state["task_summary"] = current_project_brief(state)
    for key, max_chars in {
        "active_task_id": 80,
        "active_run_id": 80,
        "active_goal": 280,
        "active_stage_reason": 220,
        "active_blocker": 220,
        "active_next_action": 220,
        "latest_message_intent": 24,
        "bound_run_id": 80,
        "bound_run_dir": 260,
        "last_bridge_sync_ts": 40,
    }.items():
        state[key] = sanitize_inline_text(str(state.get(key, "")), max_chars=max_chars)
    state["active_stage"] = sanitize_inline_text(str(state.get("active_stage", "INTAKE")), max_chars=32) or "INTAKE"
    if state["active_stage"] not in SUPPORT_ACTIVE_STAGES:
        state["active_stage"] = "INTAKE"
    state["active_stage_exit_condition"] = sanitize_inline_text(
        str(state.get("active_stage_exit_condition", SUPPORT_STAGE_EXIT_RULES.get(str(state["active_stage"]), ""))),
        max_chars=120,
    ) or SUPPORT_STAGE_EXIT_RULES.get(str(state["active_stage"]), "")
    state["active_blocker"] = state["active_blocker"] or "none"
    state["latest_message_intent"] = state["latest_message_intent"] or "continue"
    if state["latest_message_intent"] not in SUPPORT_MESSAGE_INTENTS:
        state["latest_message_intent"] = "continue"
    state["latest_conversation_mode"] = sanitize_inline_text(str(turn_memory.get("latest_conversation_mode", state.get("latest_conversation_mode", ""))), max_chars=40)


def normalize_support_session_state(doc: dict[str, Any] | None, chat_id: str) -> dict[str, Any]:
    state = default_support_session_state(chat_id)
    _merge_session_doc(state, doc)
    state["chat_id"] = chat_id
    zones = _session_zones(state)
    _normalize_project_turn_memory(state, zones)
    _normalize_raw_turns(zones["history_layers"])
    _normalize_working_memory(zones["history_layers"])
    _normalize_history_summary(zones["history_layers"])
    _normalize_user_preferences(zones["history_layers"])
    zones["session_profile"]["lang_hint"] = sanitize_inline_text(str(zones["session_profile"].get("lang_hint", "")), max_chars=12)
    zones["session_profile"]["last_source"] = sanitize_inline_text(str(zones["session_profile"].get("last_source", "")), max_chars=40)
    _normalize_provider_runtime(zones["provider_runtime_buffer"])
    try:
        state["reply_dedupe_memory"] = frontend_normalize_reply_dedupe_memory(zones["reply_dedupe_memory"], max_entries=48)
    except Exception:
        state["reply_dedupe_memory"] = {"schema_version": "ctcp-reply-dedupe-memory-v1", "turn_index": 0, "max_entries": 48, "by_intent": {}}
    _normalize_notification_state(zones["notification_state"])
    _normalize_controller_and_outbound(zones["controller_state"], zones["outbound_queue"])
    _normalize_resume_state(zones["resume_state"])
    _normalize_generation_state(zones["generation_state"])
    _normalize_frontdesk_state(state, zones)
    _normalize_top_level_state(state, zones["turn_memory"])
    return state


__all__ = ["normalize_support_session_state"]
