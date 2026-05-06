#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_io import now_iso


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def _host_attr(name: str) -> Any:
    module = _support_bot_host_module()
    return getattr(module, name, None) if module is not None else None


def sanitize_inline_text(text: str, max_chars: int = 220) -> str:
    candidate = _host_attr("sanitize_inline_text")
    if callable(candidate):
        return candidate(text, max_chars=max_chars)
    raw = re.sub(r"```[\s\S]*?```", " ", str(text or ""))
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > max_chars:
        return raw[:max_chars].rstrip()
    return raw


def frontend_normalize_frontdesk_state(doc: dict[str, Any], lang_hint: str = "") -> dict[str, Any]:
    candidate = _host_attr("frontend_normalize_frontdesk_state")
    if callable(candidate):
        return candidate(doc, lang_hint)
    return doc if isinstance(doc, dict) else {}


def frontend_default_reply_dedupe_memory(max_entries: int = 48) -> dict[str, Any]:
    candidate = _host_attr("frontend_default_reply_dedupe_memory")
    if callable(candidate):
        return candidate(max_entries=max_entries)
    return {"schema_version": "ctcp-reply-dedupe-memory-v1", "turn_index": 0, "max_entries": max_entries, "by_intent": {}}


def frontend_normalize_reply_dedupe_memory(memory: dict[str, Any], max_entries: int = 48) -> dict[str, Any]:
    candidate = _host_attr("frontend_normalize_reply_dedupe_memory")
    if callable(candidate):
        return candidate(memory, max_entries=max_entries)
    if not isinstance(memory, dict):
        return frontend_default_reply_dedupe_memory(max_entries=max_entries)
    memory["schema_version"] = sanitize_inline_text(str(memory.get("schema_version", "ctcp-reply-dedupe-memory-v1")), max_chars=64) or "ctcp-reply-dedupe-memory-v1"
    memory["turn_index"] = int(memory.get("turn_index", 0) or 0)
    memory["max_entries"] = max(12, min(200, int(memory.get("max_entries", max_entries) or max_entries)))
    if not isinstance(memory.get("by_intent"), dict):
        memory["by_intent"] = {}
    return memory


def _default_frontdesk_state() -> dict[str, Any]:
    frontdesk_state: dict[str, Any] = {}
    if frontend_normalize_frontdesk_state is not None:
        try:
            frontdesk_state = frontend_normalize_frontdesk_state({}, "")
        except Exception:
            frontdesk_state = {}
    return frontdesk_state


def _default_history_layers() -> dict[str, Any]:
    return {
        "raw_turns": [],
        "working_memory": {
            "current_goal": "",
            "current_constraints": "",
            "current_stage": "INTAKE",
            "pending_decision": "",
            "completed_results": [],
            "last_failure_reason": "",
            "next_action": "",
            "active_task_id": "",
            "active_run_id": "",
            "active_blocker": "none",
            "latest_message_intent": "continue",
        },
        "task_summary": {
            "task_goal": "",
            "confirmed_requirements": [],
            "completed_steps": [],
            "pending_steps": [],
            "current_risks": [],
            "result_location": "",
            "last_compaction_ts": "",
        },
        "user_preferences": {
            "language": "auto",
            "tone": "task_progressive",
            "initiative": "balanced",
            "verbosity": "normal",
            "avoid_mechanical": False,
            "prefer_push_to_delivery": False,
            "prefer_less_questions": False,
            "prefer_owner_report_style": True,
        },
    }


def _default_reply_dedupe_memory() -> dict[str, Any]:
    if frontend_default_reply_dedupe_memory is not None:
        return frontend_default_reply_dedupe_memory(max_entries=48)
    return {"schema_version": "ctcp-reply-dedupe-memory-v1", "turn_index": 0, "max_entries": 48, "by_intent": {}}


def _default_generation_state() -> dict[str, Any]:
    return {
        "current_state": "T0_PLAN",
        "last_trigger_text": "",
        "last_trigger_ts": "",
        "last_mode": "",
        "last_test_mode": "",
        "last_pass_fail": "",
        "last_failure_stage": "",
        "last_concise_reason": "",
        "last_command_or_entry": "",
        "last_out_dir": "",
        "last_run_dir": "",
        "last_generated_project_dir": "",
        "last_report_ts": "",
        "last_report_path": SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix(),
        "state_history": [],
    }


def default_support_session_state(chat_id: str) -> dict[str, Any]:
    return {
        "schema_version": "ctcp-support-session-state-v7",
        "chat_id": chat_id,
        "bound_run_id": "",
        "bound_run_dir": "",
        "task_summary": "",
        "active_task_id": "",
        "active_run_id": "",
        "active_goal": "",
        "active_stage": "INTAKE",
        "active_stage_reason": "default_initialized",
        "active_stage_exit_condition": SUPPORT_STAGE_EXIT_RULES["INTAKE"],
        "active_blocker": "none",
        "active_next_action": "",
        "latest_message_intent": "continue",
        "latest_conversation_mode": "",
        "last_bridge_sync_ts": "",
        "latest_support_context": {},
        "frontdesk_state": _default_frontdesk_state(),
        "session_profile": {
            "lang_hint": "",
            "last_source": "",
        },
        "project_memory": {
            "project_brief": "",
            "last_detail_turn": "",
            "last_detail_ts": "",
        },
        "project_constraints_memory": {
            "constraint_brief": "",
            "constraint_ts": "",
        },
        "execution_memory": {
            "latest_user_directive": "",
            "latest_user_directive_ts": "",
        },
        "turn_memory": {
            "latest_user_turn": "",
            "latest_user_turn_ts": "",
            "latest_conversation_mode": "",
            "latest_source": "",
        },
        "history_layers": _default_history_layers(),
        "provider_runtime_buffer": {
            "preferred_provider": "",
            "attempted_providers": [],
            "last_provider": "",
            "last_provider_status": "",
            "last_provider_reason": "",
        },
        "reply_dedupe_memory": _default_reply_dedupe_memory(),
        "notification_state": {
            "last_progress_hash": "",
            "last_progress_ts": "",
            "last_notified_run_id": "",
            "last_notified_phase": "",
            "last_auto_advance_ts": "",
            "last_seen_status_hash": "",
            "last_sent_message_hash": "",
            "last_sent_kind": "",
            "last_decision_prompt_hash": "",
            "cooldown_until_ts": "",
        },
        "controller_state": {
            "current": "BOOTSTRAP",
            "last_transition_ts": "",
            "last_reason": "",
        },
        "outbound_queue": {
            "pending_ids": [],
            "jobs": [],
        },
        "resume_state": {
            "last_resume_ts": "",
            "last_resume_source_dir": "",
            "last_resume_source_run_id": "",
            "last_resume_brief": "",
            "superseded_run_id": "",
        },
        "generation_state": _default_generation_state(),
    }

def _state_zone(session_state: dict[str, Any], key: str) -> dict[str, Any]:
    zone = session_state.get(key)
    if not isinstance(zone, dict):
        zone = {}
        session_state[key] = zone
    return zone

def current_project_brief(session_state: dict[str, Any]) -> str:
    project_memory = _state_zone(session_state, "project_memory")
    text = str(project_memory.get("project_brief", "")).strip() or str(session_state.get("task_summary", "")).strip()
    return sanitize_inline_text(text, max_chars=280)

def latest_turn_memory(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "turn_memory")

def latest_provider_runtime(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "provider_runtime_buffer")

def latest_reply_dedupe_memory(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "reply_dedupe_memory")

def latest_notification_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "notification_state")

def latest_controller_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "controller_state")

def latest_outbound_queue(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "outbound_queue")

def latest_resume_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "resume_state")

def latest_generation_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "generation_state")

def history_layers_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "history_layers")

def current_frontdesk_state(session_state: dict[str, Any]) -> dict[str, Any]:
    raw = session_state.get("frontdesk_state")
    if not isinstance(raw, dict):
        raw = {}
    if frontend_normalize_frontdesk_state is not None:
        try:
            normalized = frontend_normalize_frontdesk_state(
                raw,
                sanitize_inline_text(str(_state_zone(session_state, "session_profile").get("lang_hint", "")), max_chars=12).lower(),
            )
            session_state["frontdesk_state"] = normalized
            return normalized
        except Exception:
            pass
    session_state["frontdesk_state"] = raw
    return raw

def set_current_project_brief(session_state: dict[str, Any], text: str) -> None:
    project_memory = _state_zone(session_state, "project_memory")
    project_memory["project_brief"] = sanitize_inline_text(text, max_chars=280)
    session_state["task_summary"] = current_project_brief(session_state)

def set_project_constraints_brief(session_state: dict[str, Any], text: str) -> None:
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    project_constraints["constraint_brief"] = sanitize_inline_text(text, max_chars=280)
    project_constraints["constraint_ts"] = now_iso()

def set_execution_directive(session_state: dict[str, Any], text: str) -> None:
    execution_memory = _state_zone(session_state, "execution_memory")
    execution_memory["latest_user_directive"] = sanitize_inline_text(text, max_chars=280)
    execution_memory["latest_user_directive_ts"] = now_iso()

def record_provider_runtime(
    session_state: dict[str, Any],
    *,
    preferred_provider: str = "",
    attempted_provider: str = "",
    status: str = "",
    reason: str = "",
) -> None:
    provider_runtime = latest_provider_runtime(session_state)
    if preferred_provider:
        provider_runtime["preferred_provider"] = sanitize_inline_text(preferred_provider, max_chars=40)
    if attempted_provider:
        attempted = provider_runtime.get("attempted_providers", [])
        if not isinstance(attempted, list):
            attempted = []
        attempted.append(sanitize_inline_text(attempted_provider, max_chars=40))
        provider_runtime["attempted_providers"] = attempted[-6:]
        provider_runtime["last_provider"] = sanitize_inline_text(attempted_provider, max_chars=40)
    if status:
        provider_runtime["last_provider_status"] = sanitize_inline_text(status, max_chars=40)
    if reason:
        provider_runtime["last_provider_reason"] = sanitize_inline_text(reason, max_chars=220)

def support_active_task_state(session_state: dict[str, Any]) -> dict[str, Any]:
    frontdesk_state = current_frontdesk_state(session_state)
    summary = sanitize_inline_text(
        str(session_state.get("active_goal", "")).strip()
        or str(frontdesk_state.get("current_goal", "")).strip()
        or current_project_brief(session_state),
        max_chars=280,
    )
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    execution_memory = _state_zone(session_state, "execution_memory")
    active_task_id = sanitize_inline_text(
        str(session_state.get("active_task_id", "")).strip()
        or str(frontdesk_state.get("active_task_id", "")).strip()
        or str(session_state.get("bound_run_id", "")).strip(),
        max_chars=80,
    )
    active_run_id = sanitize_inline_text(
        str(session_state.get("active_run_id", "")).strip() or str(session_state.get("bound_run_id", "")).strip(),
        max_chars=80,
    )
    return {
        "task_summary": summary,
        "user_goal": summary,
        "run_id": active_run_id,
        "active_task_id": active_task_id,
        "active_run_id": active_run_id,
        "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
        "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220) or "none",
        "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
        "latest_message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
        "has_bound_run": bool(active_run_id),
        "current_scope": sanitize_inline_text(str(frontdesk_state.get("current_scope", "")), max_chars=280),
        "waiting_for": sanitize_inline_text(str(frontdesk_state.get("waiting_for", "")), max_chars=220),
        "project_constraints": sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=280),
        "execution_directive": sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=280),
    }


__all__ = [
    "default_support_session_state",
    "_state_zone",
    "current_project_brief",
    "latest_turn_memory",
    "latest_provider_runtime",
    "latest_reply_dedupe_memory",
    "latest_notification_state",
    "latest_controller_state",
    "latest_outbound_queue",
    "latest_resume_state",
    "latest_generation_state",
    "history_layers_state",
    "current_frontdesk_state",
    "set_current_project_brief",
    "set_project_constraints_brief",
    "set_execution_directive",
    "record_provider_runtime",
    "support_active_task_state",
]
