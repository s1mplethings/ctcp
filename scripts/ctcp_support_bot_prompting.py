#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_delivery_actions import should_expose_delivery_context
from scripts.ctcp_support_bot_io import now_iso, write_text
from scripts.ctcp_support_bot_provider import load_inbox_history
from scripts.ctcp_support_bot_public_delivery_state import public_delivery_prompt_context
from scripts.ctcp_support_bot_reply_utils import sanitize_inline_text
from scripts.ctcp_support_bot_session_state import (
    _state_zone,
    current_frontdesk_state,
    current_project_brief,
    history_layers_state,
    latest_turn_memory,
)

try:
    from frontend.frontdesk_state_machine import (
        prompt_context_from_frontdesk_state as frontend_prompt_context_from_frontdesk_state,
        reply_strategy_from_frontdesk_state as frontend_reply_strategy_from_frontdesk_state,
    )
except Exception:
    frontend_prompt_context_from_frontdesk_state = None  # type: ignore[assignment]
    frontend_reply_strategy_from_frontdesk_state = None  # type: ignore[assignment]


def _project_prompt_context(project_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    decisions = project_context.get("decisions", {})
    if not isinstance(decisions, dict):
        decisions = {}
    rows = decisions.get("decisions", [])
    if not isinstance(rows, list):
        rows = []
    return {
        "run_id": sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80),
        "goal": sanitize_inline_text(str(project_context.get("goal", "")), max_chars=260),
        "status": {
            "run_status": sanitize_inline_text(str(status.get("run_status", "")), max_chars=40),
            "verify_result": sanitize_inline_text(str(status.get("verify_result", "")), max_chars=20),
            "gate": {
                "state": sanitize_inline_text(str(gate.get("state", "")), max_chars=40),
                "owner": sanitize_inline_text(str(gate.get("owner", "")), max_chars=60),
                "reason": sanitize_inline_text(str(gate.get("reason", "")), max_chars=220),
            },
            "needs_user_decision": bool(status.get("needs_user_decision", False)),
            "decisions_needed_count": int(status.get("decisions_needed_count", 0) or 0),
        },
        "whiteboard": project_context.get("whiteboard", {}),
        "decisions_preview": [
            {
                "decision_id": sanitize_inline_text(str(item.get("decision_id", "")), max_chars=80),
                "role": sanitize_inline_text(str(item.get("role", "")), max_chars=40),
                "action": sanitize_inline_text(str(item.get("action", "")), max_chars=40),
                "question_hint": sanitize_inline_text(str(item.get("question_hint", "")), max_chars=220),
            }
            for item in rows[:2]
            if isinstance(item, dict)
        ],
    }


def default_prompt_template() -> str:
    return (
        "You are CTCP Support Lead. Return JSON only.\n"
        "Keys: reply_text,next_question,actions,debug_notes.\n"
        "Design goal: mechanical safeguards decide the boundary; the agent decides the phrasing.\n"
        "Primary support reply path is api_agent; local model reply exists only as a failover path.\n"
        "All customer-visible turns, including greetings and smalltalk, are model-authored.\n"
        "There are no preset opening or fallback customer sentences in this lane; each turn must be authored fresh from the latest user message.\n"
        "Keep the reply in the user's current primary language unless the user clearly switches.\n"
        "When session context contains an active project brief, keep it as memory only.\n"
        "On greeting, capability, or smalltalk turns, do not mention existing project memory unless the latest user message explicitly asks to continue it.\n"
        "When the current channel can send files directly, do not ask for email or off-platform transfer.\n"
        "Only promise package/screenshot/video delivery when the prompt context says public delivery is ready for this turn.\n"
        "If public delivery says package_delivery_mode is materialize_ctcp_scaffold, describe the package honestly as a CTCP-style scaffold using the provided structure hint.\n"
        "Do not describe a scaffold package as feature-complete business logic unless the prompt context explicitly says the implementation already exists.\n"
        "Short follow-up turns like 'continue', 'go ahead', or '没有，你先做着' refine execution and must not erase or pause the project unless the user explicitly says stop.\n"
        "If the prompt includes provider failover context, say plainly that the API reply path is unavailable and that you are temporarily continuing from the local path.\n"
        "reply_text must be customer-facing only and never include logs, file paths, or stack traces.\n"
        "Unless the user explicitly asks for code, do not dump source code snippets in reply_text.\n"
        "reply_text must be natural conversational prose (no rigid section labels).\n"
        "The safeguards define leakage, actionability, and question-count boundaries only; they do not require a fixed reply template.\n"
        "Ask at most one high-leverage follow-up question when route-changing details are missing.\n"
        "If package/screenshot/video delivery should happen now, use actions only: send_project_package(format=zip), send_project_screenshot(count=1-5), send_project_video(count=1-2).\n"
        "When both test-evidence screenshots and pure GUI screenshots exist, default screenshot delivery should prioritize test evidence first.\n"
        "send_project_package is allowed only when public_delivery.package_delivery_allowed is true.\n"
        "If public_delivery.package_quality_ready is false, do not ask for package confirmation; explain that quality evidence is not complete yet.\n"
    )


def should_expose_existing_project_context(conversation_mode: str, user_text: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return False
    return True


def load_prompt_template() -> str:
    if PROMPT_TEMPLATE_PATH.exists():
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
    return default_prompt_template()


def _recent_layered_turns(session_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(session_state, dict):
        return []
    layers = history_layers_state(session_state)
    raw_turns = layers.get("raw_turns", [])
    if not isinstance(raw_turns, list):
        return []
    recent: list[dict[str, Any]] = []
    for item in raw_turns[-SUPPORT_HISTORY_PROMPT_RECENT_LIMIT:]:
        if not isinstance(item, dict):
            continue
        text = sanitize_inline_text(str(item.get("text", "")), max_chars=360)
        if not text:
            continue
        recent.append(
            {
                "ts": sanitize_inline_text(str(item.get("ts", "")), max_chars=40),
                "role": sanitize_inline_text(str(item.get("role", "user")), max_chars=16) or "user",
                "source": sanitize_inline_text(str(item.get("source", "")), max_chars=40),
                "conversation_mode": sanitize_inline_text(str(item.get("conversation_mode", "")), max_chars=40),
                "message_intent": sanitize_inline_text(str(item.get("message_intent", "")), max_chars=24),
                "text": text,
            }
        )
    return recent


def _frontdesk_strategy(frontdesk_state: dict[str, Any], mode: str) -> dict[str, Any]:
    if frontend_reply_strategy_from_frontdesk_state is None:
        return {}
    try:
        strategy = frontend_reply_strategy_from_frontdesk_state(frontdesk_state, conversation_mode=mode)
    except Exception:
        return {}
    return strategy if isinstance(strategy, dict) else {}


def _add_session_context(
    context: dict[str, Any],
    *,
    session_state: dict[str, Any],
    frontdesk_state: dict[str, Any],
    recent_layered_turns: list[dict[str, Any]],
    expose_project_context: bool,
) -> None:
    project_brief = current_project_brief(session_state)
    turn_memory = latest_turn_memory(session_state)
    session_profile = _state_zone(session_state, "session_profile")
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    execution_memory = _state_zone(session_state, "execution_memory")
    history_layers = history_layers_state(session_state)
    working_memory = _state_zone(history_layers, "working_memory")
    task_summary_layer = _state_zone(history_layers, "task_summary")
    user_preferences = _state_zone(history_layers, "user_preferences")
    context["session_state"] = {
        "bound_run_id": sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80) if expose_project_context else "",
        "task_summary": project_brief if expose_project_context else "",
        "project_brief": project_brief if expose_project_context else "",
        "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80) if expose_project_context else "",
        "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80) if expose_project_context else "",
        "active_goal": sanitize_inline_text(str(session_state.get("active_goal", "")), max_chars=280) if expose_project_context else "",
        "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32) if expose_project_context else "",
        "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220) if expose_project_context else "none",
        "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220) if expose_project_context else "",
        "latest_message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
        "project_constraints": sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=260) if expose_project_context else "",
        "latest_execution_directive": sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=260) if expose_project_context else "",
        "latest_user_turn": sanitize_inline_text(str(turn_memory.get("latest_user_turn", "")), max_chars=260),
        "latest_turn_mode": sanitize_inline_text(str(turn_memory.get("latest_conversation_mode", "")), max_chars=40),
        "lang_hint": sanitize_inline_text(str(session_profile.get("lang_hint", "")), max_chars=12),
        "last_bridge_sync_ts": sanitize_inline_text(str(session_state.get("last_bridge_sync_ts", "")), max_chars=40),
    }
    context["history_layers"] = {
        "working_memory": {
            "current_goal": sanitize_inline_text(str(working_memory.get("current_goal", "")), max_chars=280) if expose_project_context else "",
            "current_constraints": sanitize_inline_text(str(working_memory.get("current_constraints", "")), max_chars=280) if expose_project_context else "",
            "current_stage": sanitize_inline_text(str(working_memory.get("current_stage", "")), max_chars=32) if expose_project_context else "",
            "pending_decision": sanitize_inline_text(str(working_memory.get("pending_decision", "")), max_chars=220) if expose_project_context else "",
            "next_action": sanitize_inline_text(str(working_memory.get("next_action", "")), max_chars=220) if expose_project_context else "",
            "active_blocker": sanitize_inline_text(str(working_memory.get("active_blocker", "none")), max_chars=220) if expose_project_context else "none",
            "latest_message_intent": sanitize_inline_text(str(working_memory.get("latest_message_intent", "continue")), max_chars=24),
        },
        "task_summary": {
            "task_goal": sanitize_inline_text(str(task_summary_layer.get("task_goal", "")), max_chars=280) if expose_project_context else "",
            "confirmed_requirements": list(task_summary_layer.get("confirmed_requirements", [])) if expose_project_context else [],
            "completed_steps": list(task_summary_layer.get("completed_steps", [])) if expose_project_context else [],
            "pending_steps": list(task_summary_layer.get("pending_steps", [])) if expose_project_context else [],
            "current_risks": list(task_summary_layer.get("current_risks", [])) if expose_project_context else [],
            "result_location": sanitize_inline_text(str(task_summary_layer.get("result_location", "")), max_chars=260) if expose_project_context else "",
        },
        "user_preferences": {
            "language": sanitize_inline_text(str(user_preferences.get("language", "auto")), max_chars=12),
            "tone": sanitize_inline_text(str(user_preferences.get("tone", "task_progressive")), max_chars=40),
            "initiative": sanitize_inline_text(str(user_preferences.get("initiative", "balanced")), max_chars=24),
            "verbosity": sanitize_inline_text(str(user_preferences.get("verbosity", "normal")), max_chars=24),
            "avoid_mechanical": bool(user_preferences.get("avoid_mechanical", False)),
            "prefer_push_to_delivery": bool(user_preferences.get("prefer_push_to_delivery", False)),
            "prefer_less_questions": bool(user_preferences.get("prefer_less_questions", False)),
            "prefer_owner_report_style": bool(user_preferences.get("prefer_owner_report_style", True)),
        },
        "recent_raw_turns": recent_layered_turns[-SUPPORT_HISTORY_PROMPT_RECENT_LIMIT:],
    }
    if frontend_prompt_context_from_frontdesk_state is not None:
        try:
            context["frontdesk_state"] = frontend_prompt_context_from_frontdesk_state(
                frontdesk_state,
                include_task_context=expose_project_context,
            )
        except Exception:
            pass


def build_support_prompt(
    run_dir: Path,
    chat_id: str,
    user_text: str,
    *,
    source: str = "",
    conversation_mode: str = "",
    session_state: dict[str, Any] | None = None,
    project_context: dict[str, Any] | None = None,
    delivery_state: dict[str, Any] | None = None,
) -> str:
    history = load_inbox_history(run_dir)
    mode = str(conversation_mode or "").strip().upper()
    frontdesk_state = current_frontdesk_state(session_state or {}) if isinstance(session_state, dict) else {}
    frontdesk_strategy = _frontdesk_strategy(frontdesk_state, mode)
    expose_project_context = bool(frontdesk_strategy.get("allow_existing_project_reference", False)) or should_expose_existing_project_context(mode, user_text)
    expose_delivery_context = should_expose_delivery_context(mode, user_text)
    recent_layered_turns = _recent_layered_turns(session_state)
    if recent_layered_turns:
        history = [{"ts": str(item.get("ts", "")), "source": str(item.get("source", "")), "text": str(item.get("text", ""))} for item in recent_layered_turns]
    if not expose_project_context and history:
        history = history[-1:]
    context = {
        "schema_version": "ctcp-support-context-v1",
        "chat_id": chat_id,
        "ts": now_iso(),
        "history": history,
        "latest_user_message": user_text,
        "source": sanitize_inline_text(source, max_chars=24),
        "conversation_mode": mode,
        "frontdesk_reply_strategy": {
            "allow_existing_project_reference": bool(frontdesk_strategy.get("allow_existing_project_reference", False)),
            "latest_turn_only": bool(frontdesk_strategy.get("latest_turn_only", (not expose_project_context))),
            "prefer_frontend_render": bool(frontdesk_strategy.get("prefer_frontend_render", False)),
            "prefer_progress_binding": bool(frontdesk_strategy.get("prefer_progress_binding", False)),
            "allow_code_output": bool(frontdesk_strategy.get("allow_code_output", False)),
        },
        "reply_guard": {
            "preset_customer_reply_allowed": False,
            "allow_existing_project_reference": expose_project_context,
            "latest_turn_only": bool(frontdesk_strategy.get("latest_turn_only", (not expose_project_context))),
            "allow_code_output": bool(frontdesk_strategy.get("allow_code_output", False)),
        },
    }
    if isinstance(session_state, dict):
        _add_session_context(
            context,
            session_state=session_state,
            frontdesk_state=frontdesk_state,
            recent_layered_turns=recent_layered_turns,
            expose_project_context=expose_project_context,
        )
    project_prompt = _project_prompt_context(project_context)
    if expose_project_context and project_prompt:
        context["project_run"] = project_prompt
    delivery_prompt = public_delivery_prompt_context(delivery_state)
    if expose_delivery_context and delivery_prompt:
        context["public_delivery"] = delivery_prompt
    prompt = (
        load_prompt_template().rstrip()
        + "\n\n# Session Context (JSON)\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n"
    )
    write_text(run_dir / SUPPORT_PROMPT_REL_PATH, prompt)
    return prompt


def build_failover_prompt(
    prompt_text: str,
    *,
    failed_provider: str,
    failed_reason: str,
    local_provider: str,
    failover_kind: str = "unavailable",
) -> str:
    payload = {
        "schema_version": "ctcp-support-provider-failover-v1",
        "failed_provider": failed_provider,
        "failed_reason": sanitize_inline_text(failed_reason, max_chars=220),
        "failed_kind": sanitize_inline_text(failover_kind, max_chars=40) or "unavailable",
        "local_provider": local_provider,
        "required_user_visible_effect": (
            "Be explicit that the API reply path is unavailable right now and that this turn is continuing from the local fallback path."
            if str(failover_kind or "").strip().lower() != "invalid_reply"
            else "Be explicit that the API path did not yield a usable customer-ready reply for this turn and that this turn is continuing from the local fallback path."
        ),
    }
    return prompt_text.rstrip() + "\n\n# Provider Failover (JSON)\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_reply_repair_prompt(
    prompt_text: str,
    *,
    conversation_mode: str,
    user_text: str,
    failed_reply: str,
) -> str:
    payload = {
        "schema_version": "ctcp-support-reply-repair-v1",
        "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
        "latest_user_message": sanitize_inline_text(user_text, max_chars=220),
        "failed_reply_excerpt": sanitize_inline_text(failed_reply, max_chars=220),
        "required_repair": (
            "The previous draft mentioned project context that the latest user message did not mention. "
            "Rewrite for only the latest user turn. Do not mention existing project memory unless the latest user message explicitly asks to continue it."
        ),
        "style_rule": "Do not use preset greeting shells. Write one natural customer-facing reply for this exact turn.",
    }
    return prompt_text.rstrip() + "\n\n# Reply Repair (JSON)\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def make_support_request(
    chat_id: str,
    user_text: str,
    prompt_text: str,
    *,
    project_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reason = prompt_text
    if len(reason) > 20000:
        reason = reason[-20000:]
    request: dict[str, Any] = {
        "role": "support_lead",
        "action": "reply",
        "target_path": SUPPORT_REPLY_PROVIDER_REL_PATH.as_posix(),
        "missing_paths": [SUPPORT_PROMPT_REL_PATH.as_posix(), SUPPORT_INBOX_REL_PATH.as_posix()],
        "reason": reason,
        "goal": f"support session {chat_id}",
        "input_text": user_text,
    }
    if isinstance(project_context, dict):
        whiteboard = project_context.get("whiteboard")
        if isinstance(whiteboard, dict):
            request["whiteboard"] = whiteboard
        status = project_context.get("status")
        if isinstance(status, dict):
            request["project_run"] = {
                "run_id": str(project_context.get("run_id", "")).strip(),
                "goal": str(project_context.get("goal", "")).strip(),
                "status": status,
            }
            run_id = str(project_context.get("run_id", "")).strip()
            if run_id:
                request["goal"] = str(project_context.get("goal", "")).strip() or f"support session {chat_id} -> {run_id}"
    return request


__all__ = [
    "_project_prompt_context",
    "default_prompt_template",
    "should_expose_existing_project_context",
    "load_prompt_template",
    "build_support_prompt",
    "build_failover_prompt",
    "build_reply_repair_prompt",
    "make_support_request",
]
