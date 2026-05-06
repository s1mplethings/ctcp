#!/usr/bin/env python3
from __future__ import annotations
import argparse
import copy
import datetime as dt
import os
import re
import socket
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from frontend.delivery_reply_actions import (
    align_reply_with_delivery_actions,
    delivery_plan_failed,
    evaluate_delivery_completion,
    inject_ready_delivery_actions,
    prioritize_screenshot_files,
    prioritize_test_screenshot_files,
    prioritize_video_files,
)
from frontend.progress_reply import humanize_progress_runtime_text, summarize_progress_evidence_refs
from frontend.telegram_http_client import telegram_post_form, telegram_post_multipart
from scripts.support_delivery_bundle_helpers import choose_public_package, package_bundle_role, parse_scaffold_run_dir, zip_directory
from tools.formal_api_lock import append_provider_ledger, formal_api_only_enabled
from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_io import *  # noqa: F403
from scripts.ctcp_support_bot_session_state import *  # noqa: F403
from scripts.ctcp_support_bot_session_normalize import *  # noqa: F403
from scripts.ctcp_support_bot_state_sync import *  # noqa: F403
from scripts.ctcp_support_bot_shared_state import *  # noqa: F403
from scripts.ctcp_support_bot_progress import *  # noqa: F403
from scripts.ctcp_support_bot_provider import *  # noqa: F403
from scripts.ctcp_support_bot_provider_runtime import *  # noqa: F403
from scripts.ctcp_support_bot_reply_utils import *  # noqa: F403
from scripts.ctcp_support_bot_prompting import *  # noqa: F403
from scripts.ctcp_support_bot_delivery_actions import *  # noqa: F403
from scripts.ctcp_support_bot_public_delivery_core import *  # noqa: F403
from scripts.ctcp_support_bot_public_delivery_state import *  # noqa: F403
from scripts.ctcp_support_bot_public_delivery_transport import *  # noqa: F403
from scripts.ctcp_support_bot_public_delivery_telegram import *  # noqa: F403
from scripts.ctcp_support_bot_t2p_state import *  # noqa: F403
from scripts.ctcp_support_bot_mode_router import *  # noqa: F403
try:
    from tools.run_paths import get_repo_slug, get_runs_root
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug, get_runs_root
if str(SCRIPTS_DIR) not in sys.path: sys.path.insert(0, str(SCRIPTS_DIR))
from support_public_delivery import build_public_delivery_transport, resolve_public_delivery_mode
try:
    from llm_core.providers import runtime as provider_runtime
    from tools.providers import api_agent, codex_agent, manual_outbox, mock_agent, ollama_agent
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from llm_core.providers import runtime as provider_runtime
    from tools.providers import api_agent, codex_agent, manual_outbox, mock_agent, ollama_agent
try:
    import ctcp_dispatch
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import ctcp_dispatch
try:
    import ctcp_front_bridge
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import ctcp_front_bridge
try:
    import ctcp_support_controller
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
import ctcp_support_controller
from ctcp_support_recovery import (
    annotate_plan_draft_recovery,
    build_frontend_backend_truth_state,
    build_stale_bound_run_context,
    inject_provider_truth_context,
    is_missing_plan_draft_context,
    latest_known_project_goal,
    plan_draft_recovery_hint,
    resolve_new_run_goal,
    should_auto_advance_project_context as should_auto_advance_project_context_impl,
)
try:
    from frontend.conversation_mode_router import (
        has_sufficient_task_signal as frontend_has_sufficient_task_signal,
        is_capability_query as frontend_is_capability_query,
        is_greeting_only as frontend_is_greeting_only,
        is_status_query as frontend_is_status_query,
        route_conversation_mode as frontend_route_conversation_mode,
    )
    from frontend.frontdesk_state_machine import (
        derive_frontdesk_state as frontend_derive_frontdesk_state,
        normalize_frontdesk_state as frontend_normalize_frontdesk_state,
        prompt_context_from_frontdesk_state as frontend_prompt_context_from_frontdesk_state,
        reply_strategy_from_frontdesk_state as frontend_reply_strategy_from_frontdesk_state,
    )
    from frontend.support_reply_policy import (
        default_reply_dedupe_memory as frontend_default_reply_dedupe_memory,
        enforce_reply_policy as frontend_enforce_reply_policy,
        normalize_reply_dedupe_memory as frontend_normalize_reply_dedupe_memory,
        render_fallback_reply as frontend_render_fallback_reply,
    )
    from frontend.response_composer import render_frontend_output
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from frontend.conversation_mode_router import (
        has_sufficient_task_signal as frontend_has_sufficient_task_signal,
        is_capability_query as frontend_is_capability_query,
        is_greeting_only as frontend_is_greeting_only,
        is_status_query as frontend_is_status_query,
        route_conversation_mode as frontend_route_conversation_mode,
    )
    from frontend.frontdesk_state_machine import (
        derive_frontdesk_state as frontend_derive_frontdesk_state,
        normalize_frontdesk_state as frontend_normalize_frontdesk_state,
        prompt_context_from_frontdesk_state as frontend_prompt_context_from_frontdesk_state,
        reply_strategy_from_frontdesk_state as frontend_reply_strategy_from_frontdesk_state,
    )
    from frontend.support_reply_policy import (
        default_reply_dedupe_memory as frontend_default_reply_dedupe_memory,
        enforce_reply_policy as frontend_enforce_reply_policy,
        normalize_reply_dedupe_memory as frontend_normalize_reply_dedupe_memory,
        render_fallback_reply as frontend_render_fallback_reply,
    )
    from frontend.response_composer import render_frontend_output
except Exception:
    frontend_has_sufficient_task_signal = None  # type: ignore[assignment]
    frontend_is_capability_query = None  # type: ignore[assignment]
    frontend_is_greeting_only = None  # type: ignore[assignment]
    frontend_is_status_query = None  # type: ignore[assignment]
    frontend_route_conversation_mode = None  # type: ignore[assignment]
    frontend_derive_frontdesk_state = None  # type: ignore[assignment]
    frontend_normalize_frontdesk_state = None  # type: ignore[assignment]
    frontend_prompt_context_from_frontdesk_state = None  # type: ignore[assignment]
    frontend_reply_strategy_from_frontdesk_state = None  # type: ignore[assignment]
    frontend_default_reply_dedupe_memory = None  # type: ignore[assignment]
    frontend_enforce_reply_policy = None  # type: ignore[assignment]
    frontend_normalize_reply_dedupe_memory = None  # type: ignore[assignment]
    frontend_render_fallback_reply = None  # type: ignore[assignment]
    render_frontend_output = None  # type: ignore[assignment]
def load_support_session_state(run_dir: Path, chat_id: str) -> dict[str, Any]:
    doc = read_json_doc(run_dir / SUPPORT_SESSION_STATE_REL_PATH)
    return normalize_support_session_state(doc, chat_id)
def save_support_session_state(run_dir: Path, state: dict[str, Any]) -> None:
    write_json(run_dir / SUPPORT_SESSION_STATE_REL_PATH, normalize_support_session_state(state, str(state.get("chat_id", "")).strip()))
def is_previous_outline_request(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    return any(p.search(raw) for p in PREVIOUS_OUTLINE_REQUEST_PATTERNS_ZH) or any(
        p.search(low) for p in PREVIOUS_OUTLINE_REQUEST_PATTERNS_EN
    )
def iter_archived_support_session_dirs(chat_id: str, current_run_dir: Path | None = None) -> list[Path]:
    sessions_root = session_run_dir(chat_id).parent
    if not sessions_root.exists():
        return []
    prefix = f"{safe_session_id(chat_id)}.backup-"
    current_resolved = current_run_dir.resolve() if current_run_dir is not None else None
    rows: list[Path] = []
    for path in sessions_root.iterdir():
        if not path.is_dir():
            continue
        if not path.name.startswith(prefix):
            continue
        if current_resolved is not None and path.resolve() == current_resolved:
            continue
        rows.append(path)
    return sorted(rows, key=lambda item: item.stat().st_mtime, reverse=True)
def resolve_archived_resume_candidate(
    *,
    chat_id: str,
    current_run_dir: Path,
    session_state: dict[str, Any],
) -> dict[str, str]:
    current_brief = current_project_brief(session_state)
    for session_dir in iter_archived_support_session_dirs(chat_id, current_run_dir=current_run_dir):
        archived_state = load_support_session_state(session_dir, chat_id)
        archived_brief = current_project_brief(archived_state)
        if not archived_brief:
            continue
        if archived_brief == current_brief:
            continue
        if is_previous_outline_request(archived_brief):
            continue
        return {
            "session_dir": str(session_dir),
            "project_brief": archived_brief,
            "bound_run_id": sanitize_inline_text(str(archived_state.get("bound_run_id", "")), max_chars=80),
        }
    return {}
def latest_resume_request_text(run_dir: Path, session_state: dict[str, Any]) -> str:
    latest_turn = sanitize_inline_text(str(latest_turn_memory(session_state).get("latest_user_turn", "")), max_chars=280)
    if latest_turn and is_previous_outline_request(latest_turn):
        return latest_turn
    execution_directive = sanitize_inline_text(
        str(_state_zone(session_state, "execution_memory").get("latest_user_directive", "")),
        max_chars=280,
    )
    if execution_directive and is_previous_outline_request(execution_directive):
        return execution_directive
    for item in reversed(load_inbox_history(run_dir, limit=12)):
        text = sanitize_inline_text(str(item.get("text", "")), max_chars=280)
        if text and is_previous_outline_request(text):
            return text
    return ""
def should_supersede_bound_run_for_resume(
    *,
    project_context: dict[str, Any] | None,
    current_goal_hint: str,
    recovered_brief: str,
) -> bool:
    current_goal = sanitize_inline_text(
        str(current_goal_hint or (project_context or {}).get("goal", "")),
        max_chars=280,
    )
    recovered = sanitize_inline_text(recovered_brief, max_chars=280)
    if not recovered:
        return False
    if current_goal == recovered:
        return False
    if not current_goal:
        return True
    if is_previous_outline_request(current_goal):
        return True
    status = project_context.get("status", {}) if isinstance(project_context, dict) else {}
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {}) if isinstance(status.get("gate", {}), dict) else {}
    run_status = str(status.get("run_status", "")).strip().lower()
    needs_user_decision = bool(status.get("needs_user_decision", False))
    gate_state = str(gate.get("state", "")).strip().lower()
    return run_status == "blocked" and gate_state == "blocked" and (not needs_user_decision)
def is_greeting_only_message(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if frontend_is_greeting_only is not None:
        try:
            if frontend_is_greeting_only(raw):
                return True
        except Exception:
            pass
    if any(p.match(raw) for p in GREETING_PATTERNS_ZH):
        return True
    if any(p.match(raw) for p in GREETING_PATTERNS_EN):
        return True
    return False
def is_low_signal_project_followup(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return True
    return any(p.match(raw) for p in LOW_SIGNAL_PROJECT_REPLY_PATTERNS)
def has_project_goal_markers(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    low = raw.lower()
    return any(token in raw for token in PROJECT_GOAL_HINTS_ZH) or any(token in low for token in PROJECT_GOAL_HINTS_EN)
def has_implementation_constraint_markers(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    low = raw.lower()
    return any(token in raw for token in IMPLEMENTATION_CONSTRAINT_HINTS_ZH) or any(
        token in low for token in IMPLEMENTATION_CONSTRAINT_HINTS_EN
    )
def is_project_execution_followup(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    if is_low_signal_project_followup(raw):
        return True
    low = raw.lower()
    return any(token in raw for token in PROJECT_EXECUTION_FOLLOWUP_HINTS_ZH) or any(
        token in low for token in PROJECT_EXECUTION_FOLLOWUP_HINTS_EN
    )
def is_previous_project_status_followup(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    return any(pattern.search(raw) for pattern in PREVIOUS_PROJECT_STATUS_PATTERNS_ZH) or any(
        pattern.search(low) for pattern in PREVIOUS_PROJECT_STATUS_PATTERNS_EN
    )
def should_refresh_project_brief(user_text: str, conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw or is_low_signal_project_followup(raw):
        return False
    if is_previous_project_status_followup(raw):
        return False
    if is_project_execution_followup(raw):
        return False
    if not has_project_goal_markers(raw):
        return False
    if frontend_has_sufficient_task_signal is not None:
        try:
            if frontend_has_sufficient_task_signal([raw], threshold=2.0):
                return True
        except Exception:
            pass
    return len(raw) >= 12
def should_capture_project_constraints(user_text: str, conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw or is_low_signal_project_followup(raw) or is_project_execution_followup(raw):
        return False
    if should_refresh_project_brief(raw, mode):
        return False
    return has_implementation_constraint_markers(raw)
def should_force_project_detail(user_text: str, session_state: dict[str, Any]) -> bool:
    if not bool(str(session_state.get("bound_run_id", "")).strip()):
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw or is_greeting_only_message(raw) or is_smalltalk_only_message(raw):
        return False
    return is_project_execution_followup(raw)
def is_domain_lift_binding_request(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    binding = any(token in raw for token in TASK_BINDING_HINTS_ZH) or any(token in low for token in TASK_BINDING_HINTS_EN)
    repair = any(token in raw for token in DOMAIN_LIFT_HINTS_ZH + GENERATION_RERUN_HINTS_ZH) or any(
        token in low for token in DOMAIN_LIFT_HINTS_EN + GENERATION_RERUN_HINTS_EN
    )
    product = has_project_goal_markers(raw) or ("产品" in raw) or ("生成" in raw) or ("project" in low) or ("generation" in low)
    execution = is_project_execution_followup(raw) or ("执行" in raw) or ("start" in low) or ("execute" in low)
    return bool((binding and product and repair) or (execution and product and repair))
def has_real_task_binding(session_state: Mapping[str, Any] | None, project_context: Mapping[str, Any] | None = None) -> bool:
    session_state = session_state if isinstance(session_state, Mapping) else {}
    project_context = project_context if isinstance(project_context, Mapping) else {}
    active_goal = sanitize_inline_text(
        str(
            session_state.get("active_goal", "")
            or session_state.get("task_summary", "")
            or dict(session_state.get("project_memory", {})).get("project_brief", "")
            or project_context.get("goal", "")
        ),
        max_chars=280,
    )
    bound_run_id = sanitize_inline_text(
        str(session_state.get("bound_run_id", "") or session_state.get("active_run_id", "") or project_context.get("run_id", "")),
        max_chars=80,
    )
    bound_run_dir = sanitize_inline_text(
        str(session_state.get("bound_run_dir", "") or project_context.get("run_dir", "")),
        max_chars=220,
    )
    return bool(active_goal and bound_run_id and bound_run_dir)
def reply_claims_task_execution(reply_text: str) -> bool:
    text = sanitize_inline_text(reply_text, max_chars=320)
    if not text:
        return False
    low = text.lower()
    return any(token in text for token in EXECUTION_CLAIM_HINTS_ZH) or any(token in low for token in EXECUTION_CLAIM_HINTS_EN)
def recover_invalid_bound_run(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    stale_run_id: str,
    error_text: str,
    trigger: str,
) -> dict[str, Any]:
    recovered = build_stale_bound_run_context(
        session_state=session_state,
        stale_run_id=stale_run_id,
        error_text=error_text,
    )
    session_state["bound_run_id"] = ""
    session_state["bound_run_dir"] = ""
    session_state["last_bridge_sync_ts"] = now_iso()
    session_state["latest_support_context"] = {
        "run_id": "",
        "goal": str(recovered.get("goal", "")),
        "status": recovered.get("status", {}),
        "runtime_state": recovered.get("runtime_state", {}),
        "whiteboard": {},
        "error": str(recovered.get("error", "")),
        "recovery": recovered.get("support_recovery", {}),
    }
    session_state["active_stage"] = "RECOVER"
    session_state["active_stage_reason"] = "stale_bound_run_cleared"
    session_state["active_stage_exit_condition"] = SUPPORT_STAGE_EXIT_RULES.get("RECOVER", "")
    session_state["active_blocker"] = sanitize_inline_text(str(recovered.get("error", "")), max_chars=220) or "none"
    session_state["active_next_action"] = sanitize_inline_text(
        str(dict(recovered.get("support_recovery", {})).get("hint", "")),
        max_chars=220,
    )
    working_memory = _state_zone(history_layers_state(session_state), "working_memory")
    working_memory["last_failure_reason"] = sanitize_inline_text(str(recovered.get("error", "")), max_chars=220)
    working_memory["next_action"] = sanitize_inline_text(session_state.get("active_next_action", ""), max_chars=220)
    append_event(
        run_dir,
        "SUPPORT_STALE_RUN_RECOVERED",
        SUPPORT_SESSION_STATE_REL_PATH.as_posix(),
        trigger=sanitize_inline_text(trigger, max_chars=40),
        stale_run_id=sanitize_inline_text(stale_run_id, max_chars=80),
        preserved_goal=sanitize_inline_text(str(recovered.get("goal", "")), max_chars=280),
    )
    append_log(
        run_dir / "logs" / "support_bot.debug.log",
        f"[{now_iso()}] stale bound run cleared trigger={trigger} run_id={stale_run_id} reason={error_text}\n",
    )
    return recovered
def fetch_support_context_with_recovery(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    bound_run_id: str,
    trigger: str,
) -> tuple[dict[str, Any], bool]:
    try:
        context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)
        return context if isinstance(context, dict) else {}, False
    except Exception as exc:
        error_text = sanitize_inline_text(str(exc), max_chars=220) or "bridge failed"
        if "run_id not found" not in error_text.lower():
            raise
        recovered = recover_invalid_bound_run(
            run_dir=run_dir,
            session_state=session_state,
            stale_run_id=bound_run_id,
            error_text=error_text,
            trigger=trigger,
        )
        return recovered, True
def is_project_create_intent(user_text: str, conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    if any(token in raw for token in PROJECT_CREATE_INTENT_HINTS_ZH):
        return True
    if any(token in low for token in PROJECT_CREATE_INTENT_HINTS_EN):
        return True
    if has_project_goal_markers(raw) and (
        ("创建" in raw)
        or ("搭建" in raw)
        or ("生成" in raw)
        or ("做一个" in raw)
        or ("create" in low)
        or ("build" in low)
        or ("generate" in low)
        or ("make a" in low)
    ):
        return True
    return False

def should_supersede_completed_bound_run_for_new_project(
    *,
    user_text: str,
    conversation_mode: str,
    project_context: dict[str, Any] | None,
) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw:
        return False
    if is_previous_project_status_followup(raw) or is_previous_outline_request(raw):
        return False
    if user_requests_project_package(raw) or user_requests_project_screenshot(raw):
        return False
    if not is_project_create_intent(raw, mode):
        return False
    if _is_final_ready_context(project_context):
        return True
    render = (project_context or {}).get("render_snapshot", {}) if isinstance(project_context, dict) else {}
    if not isinstance(render, dict):
        render = (project_context or {}).get("render_state_snapshot", {}) if isinstance(project_context, dict) else {}
    visible_state = sanitize_inline_text(str((render or {}).get("visible_state", "")), max_chars=40).upper()
    return visible_state == "DONE"

def should_trigger_t2p_state_machine(
    *,
    session_state: dict[str, Any],
    user_text: str,
    source: str,
    conversation_mode: str,
) -> bool:
    # Single-mainline policy:
    # project turns must only progress through bridge-backed CTCP run state,
    # and must not trigger the support-side fast scaffold path.
    _ = (session_state, user_text, source, conversation_mode)
    return False
def detect_conversation_mode(run_dir: Path, user_text: str, session_state: dict[str, Any]) -> str:
    active_state = support_active_task_state(session_state)
    has_bound_run = bool(str(session_state.get("bound_run_id", "")).strip())
    if frontend_route_conversation_mode is not None:
        try:
            mode = str(frontend_route_conversation_mode([user_text], user_text, active_state)).strip().upper() or "SMALLTALK"
            if mode == "STATUS_QUERY" and (not has_bound_run) and is_domain_lift_binding_request(user_text):
                return "PROJECT_DETAIL"
            if mode == "STATUS_QUERY" and (not has_bound_run) and is_project_create_intent(user_text, "PROJECT_DETAIL"):
                return "PROJECT_DETAIL"
            if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL"} and is_previous_project_status_followup(user_text):
                return "STATUS_QUERY"
            if mode == "PROJECT_INTAKE" and current_project_brief(session_state) and not should_refresh_project_brief(user_text, mode):
                return "PROJECT_DETAIL"
            if mode == "SMALLTALK" and should_force_project_detail(user_text, session_state):
                return "PROJECT_DETAIL"
            return mode
        except Exception:
            pass
    if is_greeting_only_message(user_text):
        return "GREETING"
    if frontend_is_capability_query is not None:
        try:
            if frontend_is_capability_query(user_text):
                return "CAPABILITY_QUERY"
        except Exception:
            pass
    if is_smalltalk_only_message(user_text):
        return "SMALLTALK"
    if is_previous_project_status_followup(user_text):
        return "STATUS_QUERY"
    if is_domain_lift_binding_request(user_text):
        return "PROJECT_DETAIL"
    if should_force_project_detail(user_text, session_state):
        return "PROJECT_DETAIL"
    if active_state.get("task_summary"):
        return "PROJECT_DETAIL"
    return "PROJECT_INTAKE"
def should_use_project_bridge(conversation_mode: str, session_state: dict[str, Any]) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    has_run = bool(str(session_state.get("bound_run_id", "")).strip())
    if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return True
    if mode == "STATUS_QUERY" and has_run:
        return True
    return False
def remember_resume_recovery(
    session_state: dict[str, Any],
    *,
    candidate: dict[str, str],
    superseded_run_id: str = "",
) -> None:
    resume_state = latest_resume_state(session_state)
    resume_state["last_resume_ts"] = now_iso()
    resume_state["last_resume_source_dir"] = sanitize_inline_text(str(candidate.get("session_dir", "")), max_chars=260)
    resume_state["last_resume_source_run_id"] = sanitize_inline_text(str(candidate.get("bound_run_id", "")), max_chars=80)
    resume_state["last_resume_brief"] = sanitize_inline_text(str(candidate.get("project_brief", "")), max_chars=280)
    resume_state["superseded_run_id"] = sanitize_inline_text(superseded_run_id, max_chars=80)
def maybe_recover_previous_outline_context(
    *,
    run_dir: Path,
    chat_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
    allow_history_resume: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any] | None]:
    request_text = sanitize_inline_text(user_text, max_chars=280)
    if not is_previous_outline_request(request_text) and allow_history_resume:
        request_text = latest_resume_request_text(run_dir, session_state)
    if not request_text:
        return project_context, session_state, None
    candidate = resolve_archived_resume_candidate(chat_id=chat_id, current_run_dir=run_dir, session_state=session_state)
    recovered_brief = sanitize_inline_text(str(candidate.get("project_brief", "")), max_chars=280)
    if not recovered_brief:
        return project_context, session_state, None
    bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
    current_goal_hint = sanitize_inline_text(
        str((project_context or {}).get("goal", "") if isinstance(project_context, dict) else current_project_brief(session_state)),
        max_chars=280,
    ) or current_project_brief(session_state)
    if bound_run_id and (not should_supersede_bound_run_for_resume(
        project_context=project_context,
        current_goal_hint=current_goal_hint,
        recovered_brief=recovered_brief,
    )):
        return project_context, session_state, None
    advance_steps = 0
    if str(conversation_mode or "").strip().upper() in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY", "STATUS_QUERY"}:
        advance_steps = interactive_reply_advance_steps(created=(not bound_run_id))
    refreshed = ctcp_front_bridge.ctcp_sync_support_project_turn(
        create_goal=recovered_brief,
        text=request_text,
        source=source,
        chat_id=chat_id,
        conversation_mode=conversation_mode,
        advance_steps=advance_steps,
    )
    if not isinstance(refreshed, dict):
        refreshed = {}
    created = refreshed.get("created", {}) if isinstance(refreshed.get("created", {}), dict) else {}
    new_run_id = sanitize_inline_text(str(refreshed.get("run_id", "") or created.get("run_id", "")), max_chars=80)
    session_state["bound_run_id"] = new_run_id
    session_state["bound_run_dir"] = sanitize_inline_text(
        str(refreshed.get("run_dir", "") or created.get("run_dir", "")),
        max_chars=260,
    )
    set_current_project_brief(session_state, recovered_brief)
    project_memory = _state_zone(session_state, "project_memory")
    project_memory["last_detail_turn"] = recovered_brief
    project_memory["last_detail_ts"] = now_iso()
    remember_resume_recovery(session_state, candidate=candidate, superseded_run_id=bound_run_id)
    append_event(
        run_dir,
        "SUPPORT_PREVIOUS_OUTLINE_RECOVERED",
        SUPPORT_SESSION_STATE_REL_PATH.as_posix(),
        old_run_id=bound_run_id,
        new_run_id=new_run_id,
        source_run_id=str(candidate.get("bound_run_id", "")),
    )
    session_state["last_bridge_sync_ts"] = now_iso()
    session_state["latest_support_context"] = {
        "run_id": str(refreshed.get("run_id", "")),
        "status": refreshed.get("status", {}),
        "whiteboard": refreshed.get("whiteboard", {}),
    }
    return refreshed, session_state, candidate
def sync_project_context(
    *,
    run_dir: Path,
    chat_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_context: dict[str, Any] = {}
    mode = str(conversation_mode or "").strip().upper()
    if not should_use_project_bridge(mode, session_state):
        return project_context, session_state
    bound_run_id = str(session_state.get("bound_run_id", "")).strip()
    created: dict[str, Any] | None = None
    recorded: dict[str, Any] | None = None
    advanced: dict[str, Any] | None = None
    recovered_candidate: dict[str, Any] | None = None
    bridge_error = ""
    try:
        if bound_run_id:
            project_context, recovered_stale_bound = fetch_support_context_with_recovery(
                run_dir=run_dir,
                session_state=session_state,
                bound_run_id=bound_run_id,
                trigger="interactive_sync",
            )
            if recovered_stale_bound:
                bound_run_id = ""
            elif should_supersede_completed_bound_run_for_new_project(
                user_text=user_text,
                conversation_mode=mode,
                project_context=project_context,
            ):
                old_run_id = bound_run_id
                session_state["bound_run_id"] = ""
                session_state["bound_run_dir"] = ""
                bound_run_id = ""
                project_context = {}
                append_event(
                    run_dir,
                    "SUPPORT_COMPLETED_RUN_SUPERSEDED_FOR_NEW_REQUEST",
                    SUPPORT_SESSION_STATE_REL_PATH.as_posix(),
                    old_run_id=sanitize_inline_text(old_run_id, max_chars=80),
                    new_request=sanitize_inline_text(user_text, max_chars=280),
                )
        project_context, session_state, recovered_candidate = maybe_recover_previous_outline_context(
            run_dir=run_dir,
            chat_id=chat_id,
            user_text=user_text,
            source=source,
            conversation_mode=mode if mode != "STATUS_QUERY" else "PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
            allow_history_resume=(mode == "STATUS_QUERY"),
        )
        if recovered_candidate is not None:
            bound_run_id = str(session_state.get("bound_run_id", "")).strip()
            created = project_context.get("created", {}) if isinstance(project_context, dict) else {}
            recorded = project_context.get("recorded_turn", {}) if isinstance(project_context, dict) else {}
            advanced = project_context.get("advance", {}) if isinstance(project_context, dict) else {}
        create_goal = resolve_new_run_goal(
            user_text=user_text,
            conversation_mode=mode,
            session_state=session_state,
            should_refresh_project_brief=should_refresh_project_brief,
            is_low_signal_project_followup=is_low_signal_project_followup,
            is_project_execution_followup=is_project_execution_followup,
        )
        create_goal_for_sync = ""
        if recovered_candidate is None and (not bound_run_id) and mode != "STATUS_QUERY":
            create_goal_for_sync = create_goal
        if recovered_candidate is None:
            if (not bound_run_id) and (not create_goal_for_sync):
                return project_context if isinstance(project_context, dict) else {}, session_state
            should_advance_after_turn = mode in {"PROJECT_INTAKE", "PROJECT_DETAIL"}
            create_payload_constraints: dict[str, Any] | None = None
            create_payload_intent: dict[str, Any] | None = None
            create_payload_spec: dict[str, Any] | None = None
            if (not bound_run_id) and create_goal_for_sync:
                (
                    create_payload_constraints,
                    create_payload_intent,
                    create_payload_spec,
                ) = first_turn_project_generation_payload(
                    user_text=user_text,
                    create_goal=create_goal_for_sync,
                    conversation_mode=mode,
                    session_state=session_state,
                )
            advance_steps = interactive_reply_advance_steps(
                created=bool((not bound_run_id) and create_goal_for_sync)
            ) if should_advance_after_turn else 0
            synced = ctcp_front_bridge.ctcp_sync_support_project_turn(
                run_id=bound_run_id,
                create_goal=create_goal_for_sync,
                text=user_text,
                source=source,
                chat_id=chat_id,
                conversation_mode=mode,
                advance_steps=advance_steps,
                constraints=create_payload_constraints,
                project_intent=create_payload_intent,
                project_spec=create_payload_spec,
            )
            project_context = synced if isinstance(synced, dict) else {}
            created = project_context.get("created", {}) if isinstance(project_context.get("created", {}), dict) else {}
            recorded = project_context.get("recorded_turn", {}) if isinstance(project_context.get("recorded_turn", {}), dict) else {}
            advanced = project_context.get("advance", {}) if isinstance(project_context.get("advance", {}), dict) else {}
            bound_run_id = str(project_context.get("run_id", "") or created.get("run_id", "") or bound_run_id).strip()
            if created:
                session_state["bound_run_id"] = bound_run_id
                session_state["bound_run_dir"] = str(project_context.get("run_dir", "") or created.get("run_dir", "")).strip()
                session_state["active_goal"] = sanitize_inline_text(create_goal_for_sync, max_chars=280)
                session_state["active_task_id"] = sanitize_inline_text(bound_run_id, max_chars=80)
                session_state["active_run_id"] = sanitize_inline_text(bound_run_id, max_chars=80)
                if should_refresh_project_brief(user_text, mode):
                    set_current_project_brief(session_state, user_text)
                elif not current_project_brief(session_state):
                    set_current_project_brief(session_state, create_goal_for_sync)
                append_event(run_dir, "SUPPORT_RUN_BOUND", "", run_id=bound_run_id)
            if not bound_run_id:
                return project_context if isinstance(project_context, dict) else {}, session_state
            if should_attempt_delivery_unblock_advance(project_context=project_context, user_text=user_text):
                status_for_delivery = project_context.get("status", {}) if isinstance(project_context, dict) else {}
                gate_for_delivery = status_for_delivery.get("gate", {}) if isinstance(status_for_delivery, dict) else {}
                gate_state = str(gate_for_delivery.get("state", "")).strip().lower() if isinstance(gate_for_delivery, dict) else ""
                extra_steps = 6 if gate_state == "blocked" else 4
                advanced = ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=extra_steps)
                project_context, recovered_stale_bound = fetch_support_context_with_recovery(
                    run_dir=run_dir,
                    session_state=session_state,
                    bound_run_id=bound_run_id,
                    trigger="interactive_delivery_unblock",
                )
                if recovered_stale_bound:
                    project_context["created"] = created or {}
                    project_context["recorded_turn"] = recorded or {}
                    project_context["advance"] = advanced or {}
                    return project_context, session_state
                append_event(
                    run_dir,
                    "SUPPORT_DELIVERY_UNBLOCK_ADVANCE",
                    "",
                    run_id=bound_run_id,
                    max_steps=extra_steps,
                    reason="package_requested",
                )
            annotate_plan_draft_recovery(project_context, attempted=bool(advanced))
        project_context["created"] = created or {}
        project_context["recorded_turn"] = recorded or {}
        project_context["advance"] = advanced or {}
        session_state["bound_run_id"] = bound_run_id
        session_state["bound_run_dir"] = str(project_context.get("run_dir", "") or session_state.get("bound_run_dir", "")).strip()
        if should_refresh_project_brief(user_text, mode):
            set_current_project_brief(session_state, user_text)
            project_memory = _state_zone(session_state, "project_memory")
            project_memory["last_detail_turn"] = sanitize_inline_text(user_text, max_chars=280)
            project_memory["last_detail_ts"] = now_iso()
        if should_capture_project_constraints(user_text, mode):
            set_project_constraints_brief(session_state, user_text)
        if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"} and is_project_execution_followup(user_text):
            set_execution_directive(session_state, user_text)
        elif not current_project_brief(session_state) and str(project_context.get("goal", "")).strip():
            set_current_project_brief(session_state, str(project_context.get("goal", "")))
        session_state["last_bridge_sync_ts"] = now_iso()
        session_state["latest_support_context"] = {
            "run_id": str(project_context.get("run_id", "")),
            "status": project_context.get("status", {}),
            "whiteboard": project_context.get("whiteboard", {}),
        }
    except Exception as exc:
        bridge_error = sanitize_inline_text(str(exc), max_chars=220) or "bridge failed"
        append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] bridge sync failed: {bridge_error}\n")
        if bound_run_id and "run_id not found" in bridge_error.lower():
            session_state["bound_run_id"] = ""
            session_state["bound_run_dir"] = ""
        project_context = {"error": bridge_error}
    if bridge_error:
        project_context["error"] = bridge_error
    return project_context, session_state
def sync_frontdesk_state(
    session_state: dict[str, Any],
    *,
    user_text: str,
    conversation_mode: str,
    project_context: dict[str, Any] | None = None,
    delivery_state: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if frontend_derive_frontdesk_state is None:
        return current_frontdesk_state(session_state)
    try:
        derived = frontend_derive_frontdesk_state(
            user_text=user_text,
            conversation_mode=conversation_mode,
            session_state=session_state,
            project_context=project_context,
            delivery_state=delivery_state,
            provider_result=provider_result,
        )
        session_state["frontdesk_state"] = derived
        return current_frontdesk_state(session_state)
    except Exception:
        return current_frontdesk_state(session_state)
def _normalize_reply_semantic(text: str) -> str:
    raw = re.sub(r"\s+", " ", str(text or "").strip()).lower()
    raw = re.sub(r"[，。！？!?;；:：,.\-_/\\()（）\[\]{}\"'`~]+", "", raw)
    return raw
def _contains_any_token(text: str, tokens: tuple[str, ...]) -> bool:
    low = str(text or "").lower()
    return any(str(token or "").lower() in low for token in tokens if str(token or "").strip())
def _task_like_mode(conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    return mode in {"PROJECT_DETAIL", "PROJECT_DECISION_REPLY", "STATUS_QUERY"}
def _is_final_ready_context(project_context: dict[str, Any] | None) -> bool:
    if not isinstance(project_context, dict):
        return False
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return False
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    needs_user_decision = bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0
    return (verify_result == "PASS") and (run_status in _FINAL_READY_RUN_STATUSES) and (not needs_user_decision)
def _reply_has_status_anchor(reply_text: str, binding: dict[str, Any], *, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    phase = str(binding.get("current_phase", "")).strip()
    blocker = str(binding.get("current_blocker", "")).strip()
    done_items = [str(item or "").strip() for item in list(binding.get("last_confirmed_items", []) or []) if str(item or "").strip()]
    if phase and phase in text:
        return True
    if blocker and blocker.lower() != "none" and blocker in text:
        return True
    if any(item in text for item in done_items[:2]):
        return True
    if str(lang or "").strip().lower().startswith("en"):
        return _contains_any_token(text, _TASK_PROGRESS_STATUS_MARKERS_EN)
    return _contains_any_token(text, _TASK_PROGRESS_STATUS_MARKERS_ZH)
def _reply_has_next_action(reply_text: str, binding: dict[str, Any], *, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    next_action = str(binding.get("next_action", "")).strip()
    if next_action and next_action in text:
        return True
    if str(lang or "").strip().lower().startswith("en"):
        return _contains_any_token(text, _TASK_PROGRESS_NEXT_ACTION_MARKERS_EN)
    return _contains_any_token(text, _TASK_PROGRESS_NEXT_ACTION_MARKERS_ZH)
def _reply_low_information(reply_text: str, *, lang: str) -> bool:
    text = re.sub(r"\s+", " ", str(reply_text or "").strip())
    if not text:
        return True
    low = text.lower()
    if str(lang or "").strip().lower().startswith("en"):
        token_hit = any(token in low for token in _TASK_PROGRESS_LOW_INFO_ACKS_EN)
    else:
        token_hit = any(token in text for token in _TASK_PROGRESS_LOW_INFO_ACKS_ZH)
    if not token_hit:
        return False
    if str(lang or "").strip().lower().startswith("en"):
        if any(token in low for token in ("current", "status", "phase", "next", "blocked", "run", "project")):
            return False
    else:
        if any(token in text for token in ("当前", "目前", "进度", "阶段", "卡点", "阻塞", "下一步", "已经", "后台", "项目", "run")):
            return False
    return len(text) <= 40
def _reply_has_ungrounded_completion_claim(reply_text: str, *, project_context: dict[str, Any] | None, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    if _is_final_ready_context(project_context):
        return False
    if str(lang or "").strip().lower().startswith("en"):
        return _contains_any_token(text, _TASK_PROGRESS_COMPLETION_CLAIMS_EN)
    return _contains_any_token(text, _TASK_PROGRESS_COMPLETION_CLAIMS_ZH)
def _reply_transition_incomplete(reply_text: str, *, has_next_action: bool, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    if str(lang or "").strip().lower().startswith("en"):
        transition_claimed = _contains_any_token(text, _TASK_PROGRESS_TRANSITION_MARKERS_EN)
        if not transition_claimed:
            return False
        has_reason = _contains_any_token(text, _TASK_PROGRESS_REASON_MARKERS_EN)
        has_owner = _contains_any_token(text, _TASK_PROGRESS_OWNER_MARKERS_EN)
        return (not has_reason) or (not has_owner) or (not has_next_action)
    transition_claimed = _contains_any_token(text, _TASK_PROGRESS_TRANSITION_MARKERS_ZH)
    if not transition_claimed:
        return False
    has_reason = _contains_any_token(text, _TASK_PROGRESS_REASON_MARKERS_ZH)
    has_owner = _contains_any_token(text, _TASK_PROGRESS_OWNER_MARKERS_ZH)
    return (not has_reason) or (not has_owner) or (not has_next_action)
def _compose_grounded_progress_reply(*, binding: dict[str, Any], lang: str, no_change: bool = False) -> tuple[str, str]:
    phase = sanitize_inline_text(str(binding.get("current_phase", "")), max_chars=80) or ("execution" if lang == "en" else "执行推进")
    blocker = sanitize_inline_text(humanize_progress_runtime_text(str(binding.get("current_blocker", "")), lang=lang), max_chars=160)
    next_action = sanitize_inline_text(humanize_progress_runtime_text(str(binding.get("next_action", "")), lang=lang), max_chars=220)
    evidence = sanitize_inline_text(summarize_progress_evidence_refs(binding.get("proof_refs", []), lang=lang), max_chars=220)
    done_items = [sanitize_inline_text(str(item), max_chars=80) for item in list(binding.get("last_confirmed_items", []) or [])[:3] if sanitize_inline_text(str(item), max_chars=80)]
    question_needed = str(binding.get("question_needed", "")).strip().lower() in {"yes", "true", "1"}
    blocking_question = sanitize_inline_text(str(binding.get("blocking_question", "")), max_chars=140)
    rows: list[str] = []
    next_question = ""
    if lang == "en":
        if no_change:
            rows.append(f"Current status is unchanged from the previous update; I am still in {phase} and the same blocker truth remains.")
        else:
            rows.append(f"Current phase: {phase}.")
        if done_items and not no_change:
            rows.append(f"Completed so far: {'; '.join(done_items)}.")
        if evidence: rows.append(evidence)
        if blocker and blocker.lower() != "none":
            rows.append(f"Current blocker: {blocker}.")
        else:
            rows.append("No new blocker right now.")
        if next_action:
            rows.append(f"Next step: {next_action}.")
        if question_needed and blocking_question:
            next_question = normalize_question(blocking_question)
            rows.append(f"I need one decision before I continue: {blocking_question}")
        return "\n\n".join([x for x in rows if x]).strip(), next_question
    if no_change:
        rows.append(f"当前状态和上一条一致，我还在{phase}阶段处理同一个卡点。")
    else:
        rows.append(f"目前在{phase}这个阶段。")
    if done_items and (not no_change):
        rows.append("我这边已完成：" + "、".join(done_items) + "。")
    if evidence: rows.append(evidence)
    if blocker and blocker.lower() != "none":
        rows.append(f"当前卡点是：{blocker}。")
    else:
        rows.append("暂时没有新增阻塞。")
    if next_action:
        rows.append(f"下一步我会继续处理：{next_action}。")
    if question_needed and blocking_question:
        next_question = normalize_question(blocking_question)
        rows.append(f"继续前我只需要你确认这一项：{blocking_question}")
    return "\n\n".join([x for x in rows if x]).strip(), next_question
def _load_previous_reply_snapshot(run_dir: Path) -> tuple[str, str]:
    doc = read_json_doc(run_dir / SUPPORT_REPLY_REL_PATH)
    if not isinstance(doc, dict):
        return "", ""
    previous_reply = str(doc.get("reply_text", "")).strip()
    guard = doc.get("runtime_progress_guard", {})
    if not isinstance(guard, dict):
        guard = {}
    previous_status_hash = str(guard.get("status_hash", "")).strip()
    return previous_reply, previous_status_hash
def enforce_task_progress_runtime_guard(
    *,
    run_dir: Path,
    reply_text: str,
    next_question: str,
    conversation_mode: str,
    project_context: dict[str, Any] | None,
    task_summary_hint: str = "",
    lang: str = "zh",
    question_explicit: bool = False,
) -> tuple[str, str, dict[str, Any]]:
    mode = str(conversation_mode or "").strip().upper()
    if not _task_like_mode(mode):
        return reply_text, next_question, {"applied": False, "status_hash": "", "reasons": []}
    if (not isinstance(project_context, dict)) or (not sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)):
        return reply_text, next_question, {"applied": False, "status_hash": "", "reasons": []}
    status_hash, binding = build_progress_digest(project_context=project_context, task_summary_hint=task_summary_hint)
    if not binding:
        binding = build_progress_binding(project_context=project_context, task_summary_hint=task_summary_hint)
    if not binding:
        return reply_text, next_question, {"applied": False, "status_hash": status_hash, "reasons": []}
    has_status_anchor = _reply_has_status_anchor(reply_text, binding, lang=lang)
    has_next_action = _reply_has_next_action(reply_text, binding, lang=lang)
    low_info = _reply_low_information(reply_text, lang=lang)
    transition_incomplete = _reply_transition_incomplete(reply_text, has_next_action=has_next_action, lang=lang)
    ungrounded_completion = _reply_has_ungrounded_completion_claim(reply_text, project_context=project_context, lang=lang)
    question_needed = str(binding.get("question_needed", "")).strip().lower() in {"yes", "true", "1"}
    blocking_question = sanitize_inline_text(str(binding.get("blocking_question", "")), max_chars=140)
    previous_reply, previous_status_hash = _load_previous_reply_snapshot(run_dir)
    repeated_same_state = bool(
        status_hash
        and previous_status_hash
        and status_hash == previous_status_hash
        and _normalize_reply_semantic(reply_text) == _normalize_reply_semantic(previous_reply)
    )
    reasons: list[str] = []
    if low_info:
        reasons.append("low_information_reply")
    if low_info and (not has_status_anchor):
        reasons.append("missing_status_anchor")
    if low_info and (not has_next_action):
        reasons.append("missing_next_action")
    if transition_incomplete:
        reasons.append("transition_fields_incomplete")
    if ungrounded_completion:
        reasons.append("ungrounded_completion_claim")
    if repeated_same_state:
        reasons.append("repeat_same_state")
    if question_explicit and (not question_needed) and str(next_question or "").strip():
        reasons.append("question_not_needed")
    if question_needed and (not str(next_question or "").strip()) and blocking_question:
        reasons.append("missing_blocking_question")
    if not reasons:
        return reply_text, next_question, {"applied": False, "status_hash": status_hash, "reasons": []}
    guarded_reply, guarded_question = _compose_grounded_progress_reply(
        binding=binding,
        lang=("en" if str(lang or "").strip().lower().startswith("en") else "zh"),
        no_change=("repeat_same_state" in reasons),
    )
    if (not guarded_question) and question_needed and blocking_question:
        guarded_question = normalize_question(blocking_question)
    return (
        guarded_reply or reply_text,
        guarded_question if guarded_question or question_needed else "",
        {
            "applied": True,
            "status_hash": status_hash,
            "reasons": reasons,
            "has_status_anchor": has_status_anchor,
            "has_next_action": has_next_action,
        },
    )
def enforce_task_binding_truth_guard(
    *,
    reply_text: str,
    next_question: str,
    conversation_mode: str,
    project_context: dict[str, Any] | None,
    session_state: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]]:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY", "STATUS_QUERY"}:
        return reply_text, next_question, {"applied": False, "reasons": []}
    if not reply_claims_task_execution(reply_text):
        return reply_text, next_question, {"applied": False, "reasons": []}
    if has_real_task_binding(session_state, project_context):
        return reply_text, next_question, {"applied": False, "reasons": []}
    return (
        "当前还没有绑定真实 run，状态：NEEDS_BINDING。还不能宣称已开始处理、已启动任务或已重跑测试。下一步：先完成任务绑定并写入 active_goal、bound_run_id、bound_run_dir。",
        "",
        {"applied": True, "reasons": ["execution_claim_without_binding"]},
    )
def enforce_unsolicited_code_guard(
    *,
    reply_text: str,
    next_question: str,
    conversation_mode: str,
    user_text: str,
    project_context: dict[str, Any] | None,
    task_summary_hint: str = "",
    lang: str = "zh",
) -> tuple[str, str, dict[str, Any]]:
    if not reply_looks_like_unsolicited_code(reply_text, user_text=user_text):
        return reply_text, next_question, {"applied": False, "reasons": []}
    mode = str(conversation_mode or "").strip().upper()
    use_en = str(lang or "").strip().lower().startswith("en")
    if _task_like_mode(mode) and isinstance(project_context, dict):
        status_hash, binding = build_progress_digest(project_context=project_context, task_summary_hint=task_summary_hint)
        if not binding:
            binding = build_progress_binding(project_context=project_context, task_summary_hint=task_summary_hint)
        guarded_reply, guarded_question = _compose_grounded_progress_reply(
            binding=binding,
            lang=("en" if use_en else "zh"),
            no_change=False,
        )
        if guarded_reply:
            return (
                guarded_reply,
                guarded_question or "",
                {"applied": True, "status_hash": status_hash, "reasons": ["unsolicited_code_dump"]},
            )
    if use_en:
        fallback = "You did not ask for source code in this turn, so I will not dump code right now. Next step: I will keep the update focused on status and delivery actions."
    else:
        fallback = "你这轮没有要求源码，我先不贴代码。下一步我会只给状态进展和可执行动作。"
    return fallback, "", {"applied": True, "reasons": ["unsolicited_code_dump"]}
def build_final_reply_doc(
    *,
    run_dir: Path,
    provider: str,
    provider_result: dict[str, Any],
    provider_doc: dict[str, Any] | None,
    project_context: dict[str, Any] | None = None,
    source_hint: str = "",
    conversation_mode: str = "",
    task_summary_hint: str = "",
    lang_hint: str = "",
    delivery_state: dict[str, Any] | None = None,
    frontdesk_state: dict[str, Any] | None = None,
    latest_user_message_override: str = "",
    shared_state_snapshots: Mapping[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    allow_dedupe_suppress: bool = False,
    dedupe_source_kind: str = "",
) -> dict[str, Any]:
    raw_doc = provider_doc if isinstance(provider_doc, dict) else fallback_reply_doc(provider_result)
    raw_reply_text = str(raw_doc.get("reply_text", ""))
    raw_next_question = str(raw_doc.get("next_question", ""))
    history = load_inbox_history(run_dir, limit=12)
    user_msgs = [str(item.get("text", "")).strip() for item in history if str(item.get("text", "")).strip()]
    previous_reply_text = load_last_reply_text(run_dir)
    preferred_lang = sanitize_inline_text(str(lang_hint or ""), max_chars=12).lower()
    expected_lang = preferred_lang or detect_lang_hint(*(user_msgs[-3:] or [task_summary_hint or raw_reply_text or raw_next_question]))
    lang = expected_lang or detect_lang_hint(raw_reply_text, raw_next_question, str(raw_doc.get("debug_notes", "")))
    if looks_like_garbled_text(raw_reply_text, expected_lang=expected_lang):
        raw_reply_text = ""
    if looks_like_garbled_text(raw_next_question, expected_lang=expected_lang):
        raw_next_question = ""
    pipeline_state: dict[str, Any] | None = None
    rendered_used = False
    rendered_visible_state = ""
    reply_text = ""
    next_question = ""
    question_explicit = bool(str(raw_next_question or "").strip())
    latest_user_message_for_render = sanitize_inline_text(latest_user_message_override, max_chars=280)
    if not latest_user_message_for_render:
        latest_user_message_for_render = user_msgs[-1] if user_msgs else task_summary_hint
    frontdesk_strategy: dict[str, Any] = {}
    shared_current = {}
    shared_render = {}
    if isinstance(shared_state_snapshots, Mapping):
        current_doc = shared_state_snapshots.get("current", {})
        render_doc = shared_state_snapshots.get("render", {})
        if isinstance(current_doc, Mapping):
            shared_current = dict(current_doc)
        if isinstance(render_doc, Mapping):
            shared_render = dict(render_doc)
    has_frontdesk_state = isinstance(frontdesk_state, dict) and bool(frontdesk_state)
    if frontend_reply_strategy_from_frontdesk_state is not None and has_frontdesk_state:
        try:
            frontdesk_strategy = frontend_reply_strategy_from_frontdesk_state(
                frontdesk_state or {},
                conversation_mode=conversation_mode,
            )
        except Exception:
            frontdesk_strategy = {}
    use_frontend_render = bool(frontdesk_strategy.get("prefer_frontend_render", not is_non_project_support_mode(conversation_mode)))
    if render_frontend_output is not None and use_frontend_render:
        try:
            summary_text = task_summary_hint.strip() or (user_msgs[-1] if user_msgs else raw_reply_text)
            shared_goal = sanitize_inline_text(str(shared_current.get("current_task_goal", "")), max_chars=260)
            if shared_goal:
                summary_text = shared_goal
            backend_state = build_frontend_backend_state(
                provider_result=provider_result,
                raw_doc=raw_doc,
                project_context=project_context,
                conversation_mode=conversation_mode,
                has_user_msgs=bool(user_msgs),
                task_summary_hint=summary_text,
            )
            rendered = render_frontend_output(
                raw_backend_state=backend_state,
                task_summary=summary_text,
                raw_reply_text=raw_reply_text,
                raw_next_question=raw_next_question,
                notes={
                    "lang": lang,
                    "max_questions": 2,
                    "recent_user_messages": user_msgs,
                    "latest_user_message": latest_user_message_for_render,
                    "active_task_state": {
                        "task_summary": summary_text,
                        "run_id": str(project_context.get("run_id", "")).strip() if isinstance(project_context, dict) else "",
                    },
                    "frontdesk_state": frontdesk_state or {},
                    "frontdesk_reply_strategy": frontdesk_strategy,
                    "shared_state_current": shared_current,
                    "shared_state_render": shared_render,
                },
            )
            reply_text = str(getattr(rendered, "reply_text", "")).strip()
            followups = list(getattr(rendered, "followup_questions", ()) or [])
            if followups:
                next_question = normalize_question(str(followups[0]))
                question_explicit = True
            rendered_visible_state = str(getattr(rendered, "visible_state", "")).strip()
            pipeline_state = getattr(rendered, "pipeline_state", None)
            rendered_used = True
            if (not rendered_visible_state) and isinstance(pipeline_state, dict):
                rendered_visible_state = str(pipeline_state.get("visible_state", "")).strip()
        except Exception as exc:
            append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] frontend render failed: {exc}\n")
            pipeline_state = {"error": str(exc)}
    if rendered_used:
        if not next_question:
            if rendered_visible_state in {
                "NEEDS_ONE_OR_TWO_DETAILS",
                "WAITING_FOR_DECISION",
                "BLOCKED_NEEDS_INPUT",
            }:
                next_question = normalize_question(raw_next_question)
            elif rendered_visible_state in {"UNDERSTOOD", "EXECUTING", "DONE"}:
                next_question = ""
            else:
                next_question = normalize_question(raw_next_question)
    elif not next_question:
        next_question = normalize_question(raw_next_question)
    if not reply_text:
        reply_text = normalize_reply_text(raw_reply_text, next_question)
    latest_user_text = user_msgs[-1] if user_msgs else task_summary_hint
    zip_confirmation_intent = is_zip_confirmation_after_recent_package_request(user_msgs)
    actions = synthesize_delivery_actions(
        actions=normalize_actions(raw_doc.get("actions")),
        user_text=latest_user_text,
        delivery_state=delivery_state,
        conversation_mode=conversation_mode,
        zip_confirmation_intent=zip_confirmation_intent,
    )
    actions = inject_ready_delivery_actions(
        actions=actions,
        project_context=project_context,
        delivery_state=delivery_state,
        source_hint=source_hint,
    )
    runtime_guard: dict[str, Any] = {"applied": False, "status_hash": "", "reasons": []}
    if not str(provider_result.get("degraded_from", "")).strip():
        reply_text, next_question, runtime_guard = enforce_task_progress_runtime_guard(
            run_dir=run_dir,
            reply_text=reply_text,
            next_question=next_question,
            conversation_mode=conversation_mode,
            project_context=project_context,
            task_summary_hint=task_summary_hint,
            lang=lang,
            question_explicit=question_explicit,
        )
    reply_text = align_reply_with_delivery_actions(reply_text, actions=actions, source_hint=source_hint)
    reply_text = append_delivery_preview_confirmation_note(
        reply_text,
        user_text=latest_user_text,
        delivery_state=delivery_state,
        actions=actions,
        zip_confirmation_intent=zip_confirmation_intent,
    )
    reply_intent = ""
    reply_template_id = ""
    reply_policy: dict[str, Any] = {"fallback_used": False, "reasons": []}
    if frontend_enforce_reply_policy is not None:
        try:
            policy_project_context = inject_provider_truth_context(
                project_context=project_context,
                provider_result=provider_result,
                raw_doc=raw_doc,
            )
            reply_memory = latest_reply_dedupe_memory(session_state) if isinstance(session_state, dict) else {}
            policy_out = frontend_enforce_reply_policy(
                reply_text=reply_text,
                next_question=next_question,
                conversation_mode=conversation_mode,
                lang_hint=lang,
                project_context=policy_project_context,
                provider_status=str(provider_result.get("status", "")).strip(),
                previous_reply_text=previous_reply_text,
                reply_memory=reply_memory,
                now_ts=now_iso(),
                provider_mode=provider,
                source_kind=sanitize_inline_text(
                    dedupe_source_kind
                    or ("fallback" if str(provider_result.get("status", "")).strip().lower() in {"exec_failed", "failed", "error", "deferred"} else "provider"),
                    max_chars=24,
                ),
                allow_suppress=bool(allow_dedupe_suppress),
            )
            policy_reply_text = str(policy_out.get("reply_text", "")).strip()
            policy_next_question = str(policy_out.get("next_question", "")).strip()
            if bool(policy_out.get("suppressed", False)):
                reply_text = ""
                next_question = ""
            elif policy_reply_text:
                reply_text = policy_reply_text
                next_question = normalize_question(policy_next_question) if policy_next_question else ""
            elif policy_next_question:
                next_question = normalize_question(policy_next_question)
            reply_intent = sanitize_inline_text(str(policy_out.get("intent", "")), max_chars=32).lower()
            reply_template_id = sanitize_inline_text(str(policy_out.get("template_id", "")), max_chars=80)
            reply_policy = {
                "fallback_used": bool(policy_out.get("fallback_used", False)),
                "reasons": [
                    sanitize_inline_text(str(item), max_chars=60)
                    for item in list(policy_out.get("reasons", []))
                    if sanitize_inline_text(str(item), max_chars=60)
                ][:8],
                "dedupe_action": sanitize_inline_text(str(policy_out.get("dedupe_action", "send")), max_chars=24) or "send",
                "similarity_max": float(policy_out.get("similarity_max", 0.0) or 0.0),
                "suppressed": bool(policy_out.get("suppressed", False)),
            }
            if isinstance(session_state, dict):
                mem = policy_out.get("reply_memory", {})
                if isinstance(mem, dict):
                    session_state["reply_dedupe_memory"] = mem
        except Exception as exc:
            reply_policy = {"fallback_used": False, "reasons": [f"policy_error:{sanitize_inline_text(str(exc), max_chars=80)}"]}
    binding_guard = {"applied": False, "reasons": []}
    if not str(provider_result.get("degraded_from", "")).strip():
        reply_text, next_question, binding_guard = enforce_task_binding_truth_guard(
            reply_text=reply_text,
            next_question=next_question,
            conversation_mode=conversation_mode,
            project_context=project_context,
            session_state=session_state,
        )
        if bool(binding_guard.get("applied", False)):
            runtime_guard = dict(runtime_guard) if isinstance(runtime_guard, dict) else {"applied": False, "status_hash": "", "reasons": []}
            runtime_guard["applied"] = True
            reasons = list(runtime_guard.get("reasons", []))
            for item in list(binding_guard.get("reasons", [])):
                if str(item).strip() and item not in reasons:
                    reasons.append(item)
            runtime_guard["reasons"] = reasons
    reply_text, next_question, code_guard = enforce_unsolicited_code_guard(
        reply_text=reply_text,
        next_question=next_question,
        conversation_mode=conversation_mode,
        user_text=latest_user_text,
        project_context=project_context,
        task_summary_hint=task_summary_hint,
        lang=lang,
    )
    if bool(code_guard.get("applied", False)):
        runtime_guard = dict(runtime_guard) if isinstance(runtime_guard, dict) else {"applied": False, "status_hash": "", "reasons": []}
        runtime_guard["applied"] = True
        if str(code_guard.get("status_hash", "")).strip():
            runtime_guard["status_hash"] = str(code_guard.get("status_hash", "")).strip()
        reasons = list(runtime_guard.get("reasons", []))
        for item in list(code_guard.get("reasons", [])):
            if str(item).strip() and item not in reasons:
                reasons.append(item)
        runtime_guard["reasons"] = reasons
    debug_notes = sanitize_inline_text(str(raw_doc.get("debug_notes", "")), max_chars=400)
    provider_status = str(provider_result.get("status", "")).strip()
    provider_reason = sanitize_inline_text(str(provider_result.get("reason", "")), max_chars=220)
    debug_combined = f"provider={provider}; status={provider_status}; reason={provider_reason}"
    degraded_from = sanitize_inline_text(str(provider_result.get("degraded_from", "")), max_chars=40)
    degraded_reason = sanitize_inline_text(str(provider_result.get("degraded_reason", "")), max_chars=180)
    degraded_kind = sanitize_inline_text(str(provider_result.get("degraded_kind", "")), max_chars=40)
    if degraded_from:
        debug_combined += f"; degraded_from={degraded_from}"
    if degraded_reason:
        debug_combined += f"; degraded_reason={degraded_reason}"
    if degraded_kind:
        debug_combined += f"; degraded_kind={degraded_kind}"
    if debug_notes:
        debug_combined += f"; notes={debug_notes}"
    if isinstance(pipeline_state, dict):
        selected = sanitize_inline_text(str(pipeline_state.get("selected_requirement_source", "")), max_chars=160)
        visible = sanitize_inline_text(str(pipeline_state.get("visible_state", "")), max_chars=60)
        if selected:
            debug_combined += f"; selected_requirement={selected}"
        if visible:
            debug_combined += f"; visible_state={visible}"
    if isinstance(frontdesk_state, dict):
        frontdesk_name = sanitize_inline_text(str(frontdesk_state.get("state", "")), max_chars=40)
        interrupt_kind = sanitize_inline_text(str(frontdesk_state.get("interrupt_kind", "")), max_chars=40)
        if frontdesk_name:
            debug_combined += f"; frontdesk_state={frontdesk_name}"
        if interrupt_kind:
            debug_combined += f"; interrupt_kind={interrupt_kind}"
    if isinstance(project_context, dict):
        run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
        if run_id:
            debug_combined += f"; run_id={run_id}"
        whiteboard = project_context.get("whiteboard", {})
        if isinstance(whiteboard, dict):
            hit_count = len(list(whiteboard.get("hits", []))) if isinstance(whiteboard.get("hits", []), list) else 0
            if hit_count:
                debug_combined += f"; whiteboard_hits={hit_count}"
    if isinstance(runtime_guard, dict) and bool(runtime_guard.get("applied", False)):
        reasons = ",".join(str(item) for item in list(runtime_guard.get("reasons", []))[:6] if str(item).strip())
        if reasons:
            debug_combined += f"; runtime_guard={reasons}"
    if reply_intent:
        debug_combined += f"; reply_intent={reply_intent}"
    if bool(reply_policy.get("fallback_used", False)):
        debug_combined += "; reply_policy=fallback"
    policy_reasons = ",".join(str(item) for item in list(reply_policy.get("reasons", []))[:6] if str(item).strip())
    if policy_reasons:
        debug_combined += f"; reply_policy_reasons={policy_reasons}"
    if reply_template_id:
        debug_combined += f"; template_id={reply_template_id}"
    if str(reply_policy.get("dedupe_action", "")).strip():
        debug_combined += f"; dedupe_action={sanitize_inline_text(str(reply_policy.get('dedupe_action', '')), max_chars=24)}"
    if bool(reply_policy.get("suppressed", False)):
        debug_combined += "; dedupe_suppressed=true"
    append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] {debug_combined}\n")
    reply_text = align_reply_with_delivery_actions(reply_text, actions=actions, source_hint=source_hint)
    return {
        "schema_version": "ctcp-support-reply-v1",
        "ts": now_iso(),
        "provider": provider,
        "provider_status": provider_status,
        "reply_text": reply_text,
        "next_question": next_question,
        "actions": actions,
        "reply_intent": reply_intent or "acknowledge_user",
        "reply_template_id": reply_template_id,
        "reply_policy": reply_policy,
        "debug_notes": debug_combined,
        "runtime_progress_guard": runtime_guard if isinstance(runtime_guard, dict) else {},
    }
def process_message(
    *,
    chat_id: str,
    user_text: str,
    source: str,
    provider_override: str = "",
) -> tuple[dict[str, Any], Path]:
    user_text = utf8_clean(user_text)
    run_dir = session_run_dir(chat_id)
    ensure_layout(run_dir)
    session_state = load_support_session_state(run_dir, chat_id)
    append_jsonl(
        run_dir / SUPPORT_INBOX_REL_PATH,
        {
            "ts": now_iso(),
            "chat_id": chat_id,
            "source": source,
            "text": user_text,
        },
    )
    append_event(run_dir, "SUPPORT_MESSAGE_RECEIVED", SUPPORT_INBOX_REL_PATH.as_posix(), source=source)
    config, cfg_msg = load_dispatch_config(run_dir)
    append_log(run_dir / "logs" / "support_bot.dispatch.log", f"[{now_iso()}] load_dispatch_config: {cfg_msg}\n")
    detected_mode = detect_conversation_mode(run_dir, user_text, session_state)
    conversation_mode = maybe_override_conversation_mode_with_model(
        run_dir=run_dir,
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        detected_mode=detected_mode,
        session_state=session_state,
        config=config,
        provider_override=provider_override,
    )
    record_turn_memory(session_state, user_text=user_text, source=source, conversation_mode=conversation_mode)
    project_context, session_state = sync_project_context(
        run_dir=run_dir,
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
    )
    delivery_state = collect_public_delivery_state(
        session_state=session_state,
        project_context=project_context,
        source=source,
        support_run_dir=run_dir,
    )
    frontdesk_state = sync_frontdesk_state(
        session_state,
        user_text=user_text,
        conversation_mode=conversation_mode,
        project_context=project_context,
        delivery_state=delivery_state,
    )
    sync_active_task_truth(
        session_state,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        delivery_state=delivery_state,
    )
    shared_state_snapshots = sync_shared_state_workspace(
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
    )
    save_support_session_state(run_dir, session_state)
    prompt_text = build_support_prompt(
        run_dir,
        chat_id,
        user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
        project_context=project_context,
        delivery_state=delivery_state,
    )
    candidates = support_provider_candidates(config, override=provider_override)
    record_provider_runtime(session_state, preferred_provider=(candidates[0] if candidates else PRIMARY_SUPPORT_PROVIDER))
    request = make_support_request(chat_id, user_text, prompt_text, project_context=project_context)
    provider_output = run_dir / SUPPORT_REPLY_PROVIDER_REL_PATH
    provider = candidates[0]
    result: dict[str, Any] = {"status": "exec_failed", "reason": "model providers not executed"}
    provider_doc: dict[str, Any] | None = None
    attempt_errors: list[str] = []
    expected_lang = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
    if not expected_lang:
        expected_lang = detect_lang_hint(user_text, current_project_brief(session_state))
    api_failover: dict[str, str] | None = None
    api_repair_attempted = False
    for idx, candidate in enumerate(candidates, start=1):
        provider = candidate
        append_event(run_dir, "SUPPORT_PROVIDER_SELECTED", "", provider=provider, attempt=idx)
        if provider_output.exists():
            try:
                provider_output.unlink()
            except Exception:
                pass
        current_request = request
        if api_failover and provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
            failover_prompt = build_failover_prompt(
                prompt_text,
                failed_provider=str(api_failover.get("failed_provider", PRIMARY_SUPPORT_PROVIDER)),
                failed_reason=str(api_failover.get("failed_reason", "")),
                local_provider=provider,
                failover_kind=str(api_failover.get("failed_kind", "unavailable")),
            )
            write_text(run_dir / SUPPORT_PROMPT_REL_PATH, failover_prompt)
            current_request = make_support_request(chat_id, user_text, failover_prompt, project_context=project_context)
            current_request["provider_failover"] = {
                "failed_provider": str(api_failover.get("failed_provider", PRIMARY_SUPPORT_PROVIDER)),
                "failed_reason": str(api_failover.get("failed_reason", "")),
                "failed_kind": str(api_failover.get("failed_kind", "unavailable")),
                "local_provider": provider,
            }
        current = execute_provider(provider=provider, run_dir=run_dir, request=current_request, config=config)
        ledger_result = dict(current)
        if api_failover and provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
            ledger_result["fallback_used"] = True
        append_provider_ledger(
            run_dir,
            role="support_lead",
            action="support_reply",
            provider_used=provider,
            result=ledger_result,
        )
        result = current
        log_provider_result(run_dir, provider, current, f"attempt_{idx}")
        record_provider_runtime(
            session_state,
            attempted_provider=provider,
            status=str(current.get("status", "")),
            reason=str(current.get("reason", "")),
        )
        status = str(current.get("status", "")).strip()
        if status in {"outbox_created", "outbox_exists", "pending", "deferred"}:
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": str(current.get("reason", "")).strip() or status,
                    "failed_kind": classify_api_failover_kind(status=status, reason=str(current.get("reason", "")).strip() or status),
                }
                attempt_errors.append(f"{provider} {status}")
                continue
            if provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
                attempt_errors.append(f"{provider} {status}")
                continue
            provider_doc = deferred_support_reply_doc(provider, current)
            break
        if status != "executed":
            reason = str(current.get("reason", "")).strip() or f"{provider} execution failed"
            attempt_errors.append(reason)
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": reason,
                    "failed_kind": classify_api_failover_kind(status=status, reason=reason),
                }
            continue
        doc = read_json_doc(provider_output)
        if not isinstance(doc, dict):
            reason = f"{provider} output missing/invalid json"
            attempt_errors.append(reason)
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": reason,
                    "failed_kind": "invalid_reply",
                }
            continue
        doc, had_mojibake = sanitize_provider_doc(doc)
        validation_kind, validation_reason = validate_provider_reply_doc(
            doc=doc,
            had_mojibake=had_mojibake,
            expected_lang=expected_lang,
            conversation_mode=conversation_mode,
            user_text=user_text,
        )
        if validation_kind:
            reason = f"{provider} {validation_reason}"
            attempt_errors.append(reason)
            if (
                provider == PRIMARY_SUPPORT_PROVIDER
                and validation_kind == "stale_context"
                and is_non_project_support_mode(conversation_mode)
                and not api_repair_attempted
            ):
                api_repair_attempted = True
                repair_prompt = build_reply_repair_prompt(
                    prompt_text,
                    conversation_mode=conversation_mode,
                    user_text=user_text,
                    failed_reply=str(doc.get("reply_text", "")),
                )
                write_text(run_dir / SUPPORT_PROMPT_REL_PATH, repair_prompt)
                repair_request = make_support_request(chat_id, user_text, repair_prompt, project_context=project_context)
                repair_request["reply_guard"] = {
                    "guard_reason": validation_reason,
                    "conversation_mode": conversation_mode,
                    "latest_turn_only": True,
                }
                repaired = execute_provider(provider=provider, run_dir=run_dir, request=repair_request, config=config)
                result = repaired
                log_provider_result(run_dir, provider, repaired, f"attempt_{idx}_repair")
                record_provider_runtime(
                    session_state,
                    attempted_provider=provider,
                    status=str(repaired.get("status", "")),
                    reason=str(repaired.get("reason", "")),
                )
                repair_status = str(repaired.get("status", "")).strip()
                if repair_status == "executed":
                    repaired_doc = read_json_doc(provider_output)
                    if isinstance(repaired_doc, dict):
                        repaired_doc, repaired_had_mojibake = sanitize_provider_doc(repaired_doc)
                        repair_kind, repair_reason = validate_provider_reply_doc(
                            doc=repaired_doc,
                            had_mojibake=repaired_had_mojibake,
                            expected_lang=expected_lang,
                            conversation_mode=conversation_mode,
                            user_text=user_text,
                        )
                        if not repair_kind:
                            current = repaired
                            result = current
                            provider_doc = repaired_doc
                            break
                        reason = f"{provider} {repair_reason}"
                    else:
                        reason = f"{provider} output missing/invalid json after repair"
                else:
                    reason = str(repaired.get("reason", "")).strip() or f"{provider} repair execution failed"
                attempt_errors.append(reason)
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": reason,
                    "failed_kind": "invalid_reply",
                }
            continue
        if provider in LOCAL_SUPPORT_REPLY_PROVIDERS and api_failover:
            current["degraded_from"] = str(api_failover.get("failed_provider", PRIMARY_SUPPORT_PROVIDER))
            current["degraded_reason"] = str(api_failover.get("failed_reason", ""))
            current["degraded_kind"] = str(api_failover.get("failed_kind", "unavailable"))
        provider_doc = doc
        break
    if not isinstance(provider_doc, dict):
        joined = " | ".join(attempt_errors[-3:])
        result = {
            "status": "exec_failed",
            "reason": joined or str(result.get("reason", "")).strip() or "model providers unavailable",
        }
        if api_failover and resolve_local_support_fallback(config):
            result["local_provider"] = resolve_local_support_fallback(config)
            result["api_failure_kind"] = str(api_failover.get("failed_kind", "unavailable"))
        provider_doc = model_unavailable_reply_doc(result, lang_hint=expected_lang)
    final_doc = build_final_reply_doc(
        run_dir=run_dir,
        provider=provider,
        provider_result=result,
        provider_doc=provider_doc,
        project_context=project_context,
        source_hint=source,
        conversation_mode=conversation_mode,
        task_summary_hint=current_project_brief(session_state),
        lang_hint=str(_state_zone(session_state, "session_profile").get("lang_hint", "")),
        delivery_state=delivery_state,
        frontdesk_state=frontdesk_state,
        shared_state_snapshots=shared_state_snapshots,
        session_state=session_state,
        allow_dedupe_suppress=False,
        dedupe_source_kind="provider",
    )
    if formal_api_only_enabled():
        formal_failed = (
            provider != PRIMARY_SUPPORT_PROVIDER
            or str(result.get("status", "")).strip() != "executed"
            or bool(result.get("fallback_used", False))
        )
        if formal_failed:
            final_doc["formal_api_only_failed"] = True
            final_doc["formal_api_only_failure_reason"] = (
                str(result.get("reason", "")).strip()
                or f"formal_api_only requires {PRIMARY_SUPPORT_PROVIDER} executed without fallback for support_reply"
            )
    write_json(run_dir / SUPPORT_REPLY_REL_PATH, final_doc)
    frontdesk_state = sync_frontdesk_state(
        session_state,
        user_text=user_text,
        conversation_mode=conversation_mode,
        project_context=project_context,
        delivery_state=delivery_state,
        provider_result=result,
    )
    sync_active_task_truth(
        session_state,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        delivery_state=delivery_state,
        provider_result=result,
        assistant_reply_text=sanitize_inline_text(str(final_doc.get("reply_text", "")), max_chars=360),
    )
    shared_state_snapshots = sync_shared_state_workspace(
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
    )
    remember_progress_notification(
        session_state,
        project_context=project_context,
        task_summary_hint=current_project_brief(session_state),
    )
    session_state["latest_support_context"] = {
        "run_id": str(project_context.get("run_id", "")) if isinstance(project_context, dict) else "",
        "provider_status": str(final_doc.get("provider_status", "")),
        "conversation_mode": conversation_mode,
        "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80),
        "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80),
        "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
        "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220),
        "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
        "message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
        "frontdesk_state": str(frontdesk_state.get("state", "")),
        "interrupt_kind": str(frontdesk_state.get("interrupt_kind", "")),
        "package_ready": bool(delivery_state.get("package_ready", False)),
        "package_delivery_allowed": bool(delivery_state.get("package_delivery_allowed", False)),
        "package_blocked_reason": sanitize_inline_text(str(delivery_state.get("package_blocked_reason", "")), max_chars=120),
        "package_delivery_mode": str(delivery_state.get("package_delivery_mode", "")).strip(),
        "package_structure_hint": list(delivery_state.get("package_structure_hint", [])),
        "screenshot_ready": bool(delivery_state.get("screenshot_ready", False)),
        "video_ready": bool(delivery_state.get("video_ready", False)),
        "t2p_state": sanitize_inline_text(str(latest_generation_state(session_state).get("current_state", "")), max_chars=32),
        "t2p_pass_fail": sanitize_inline_text(str(latest_generation_state(session_state).get("last_pass_fail", "")), max_chars=12),
        "t2p_failure_stage": sanitize_inline_text(
            str(latest_generation_state(session_state).get("last_failure_stage", "")),
            max_chars=40,
        ),
        "t2p_report_path": sanitize_inline_text(
            str(latest_generation_state(session_state).get("last_report_path", "")),
            max_chars=220,
        ),
        "shared_state_task_id": sanitize_inline_text(str((shared_state_snapshots or {}).get("task_id", "")), max_chars=80),
        "shared_state_workspace_root": sanitize_inline_text(str((shared_state_snapshots or {}).get("workspace_root", "")), max_chars=260),
    }
    save_support_session_state(run_dir, session_state)
    append_event(run_dir, "SUPPORT_REPLY_WRITTEN", SUPPORT_REPLY_REL_PATH.as_posix(), provider=provider)
    return final_doc, run_dir
def parse_allowlist(raw: str) -> set[int] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    out: set[int] = set()
    for part in text.split(","):
        item = part.strip()
        if not item:
            continue
        try:
            out.add(int(item))
        except Exception:
            continue
    return out or None
def iter_telegram_support_chat_ids(allowlist: set[int] | None) -> list[int]:
    if allowlist is not None:
        return sorted(int(item) for item in allowlist)
    sessions_root = session_run_dir("telegram").parent
    if not sessions_root.exists():
        return []
    out: list[int] = []
    for path in sessions_root.iterdir():
        if not path.is_dir() or ".backup-" in path.name:
            continue
        try:
            out.append(int(path.name))
        except Exception:
            continue
    return sorted(set(out))

def telegram_support_sessions_root() -> Path:
    return session_run_dir("telegram").parent

def clear_telegram_support_history() -> dict[str, Any]:
    sessions_root = telegram_support_sessions_root()
    ensure_external_run_dir(sessions_root)
    cleared: list[str] = []
    failed: list[dict[str, str]] = []
    if not sessions_root.exists():
        return {"sessions_root": str(sessions_root), "cleared_count": 0, "failed": []}
    for path in sessions_root.iterdir():
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            else:
                continue
            cleared.append(path.name)
        except Exception as exc:
            failed.append({"path": str(path), "error": sanitize_inline_text(str(exc), max_chars=220)})
    return {
        "sessions_root": str(sessions_root),
        "cleared_count": len(cleared),
        "cleared": cleared[:50],
        "failed": failed,
    }

def build_grounded_status_reply_doc(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build status reply doc for proactive progress updates."""
    delivery_state = collect_public_delivery_state(
        session_state=session_state,
        project_context=project_context,
        source="telegram",
        support_run_dir=run_dir,
    )
    lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
    synthetic_status_turn = "what's the latest progress?" if lang_hint.startswith("en") else "现在做到什么程度了"
    # Proactive status updates use grounded render path; provider draft is optional.
    result = {"status": "executed", "reason": "grounded_status_reply"}
    provider_doc = {"reply_text": "", "next_question": "", "actions": [], "debug_notes": "grounded_status_reply"}
    # Proactive status render should not mutate live frontdesk/session state.
    shadow_state = copy.deepcopy(session_state)
    frontdesk_state = sync_frontdesk_state(
        shadow_state,
        user_text=synthetic_status_turn,
        conversation_mode="STATUS_QUERY",
        project_context=project_context,
        delivery_state=delivery_state,
    )
    doc = build_final_reply_doc(
        run_dir=run_dir,
        provider=str(result.get("provider", "api_agent")),
        provider_result=result,
        provider_doc=provider_doc,
        project_context=project_context,
        source_hint="telegram",
        conversation_mode="STATUS_QUERY",
        task_summary_hint=current_project_brief(session_state),
        lang_hint=lang_hint,
        delivery_state=delivery_state,
        frontdesk_state=frontdesk_state,
        latest_user_message_override=synthetic_status_turn,
        session_state=shadow_state,
        allow_dedupe_suppress=True,
        dedupe_source_kind="proactive",
    )
    return doc
def _controller_decision_reply_text(*, project_context: dict[str, Any] | None, decision_prompt: str, lang_hint: str) -> str:
    prompt = sanitize_inline_text(decision_prompt, max_chars=280)
    if not prompt and isinstance(project_context, dict):
        status = project_context.get("status", {})
        if isinstance(status, dict):
            gate = status.get("gate", {})
            if isinstance(gate, dict):
                prompt = sanitize_inline_text(str(gate.get("reason", "")), max_chars=280)
    if not prompt:
        prompt = "这一步需要你确认一个关键选择。"
    if frontend_render_fallback_reply is not None:
        try:
            rendered = frontend_render_fallback_reply(
                intent="ask_decision",
                lang_hint=str(lang_hint or "").strip().lower() or "zh",
                project_context=project_context or {},
                next_question=prompt,
                previous_reply_text="",
            )
            text = str(rendered.get("reply_text", "")).strip()
            if text:
                return text
        except Exception:
            pass
    if str(lang_hint or "").strip().lower().startswith("en"):
        return f"We need one decision from you before I can continue: {prompt}"
    return f"现在这一步需要你先拍一个板：{prompt}"
def _normalize_proactive_progress_reply_text(reply_text: str, *, lang_hint: str = "") -> str:
    return ctcp_support_controller.normalize_proactive_progress_reply_text(
        reply_text,
        lang_hint=lang_hint,
        leak_tokens=_PROACTIVE_INTERNAL_GATE_LEAK_TOKENS,
    )
def _handle_outbound_send_failure_with_limit(
    *,
    session_state: dict[str, Any],
    job: dict[str, Any],
    kind: str,
    error_text: str,
) -> bool:
    # Returns True when the job should keep requeueing, False when dropped/suppressed.
    clean_kind = sanitize_inline_text(kind, max_chars=24).lower() or "progress"
    limit = int(dict(SUPPORT_OUTBOUND_REQUEUE_MAX_RETRIES).get(clean_kind, 2) or 2)
    try:
        fail_count = int(job.get("send_fail_count", 0) or 0)
    except Exception:
        fail_count = 0
    fail_count += 1
    job["send_fail_count"] = fail_count
    job["last_send_error"] = sanitize_inline_text(str(error_text), max_chars=220)
    job["last_send_error_ts"] = now_iso()
    if fail_count <= max(1, limit):
        ctcp_support_controller.requeue_outbound_job(session_state, job, sanitize_inline_text=sanitize_inline_text)
        return True
    # Drop the stuck stage job after retry cap and suppress same-hash repeats until status changes.
    ctcp_support_controller.mark_job_sent(
        session_state,
        job,
        now_ts=now_iso(),
        cooldown_sec=SUPPORT_OUTBOUND_DROP_COOLDOWN_SEC,
    )
    return False
def _emit_controller_outbound_jobs(
    *,
    tg: TelegramClient,
    chat_id: int,
    run_dir: Path,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
    auto_advanced: bool,
    recovered_candidate: dict[str, Any] | None,
) -> int:
    jobs = ctcp_support_controller.pop_outbound_jobs(session_state, max_jobs=4)
    if not jobs:
        return 0
    sent = 0
    for job in jobs:
        kind = sanitize_inline_text(str(job.get("kind", "")), max_chars=24).lower()
        reply_text = ""
        provider_status = "executed"
        reply_actions: list[dict[str, Any]] = []
        reply_delivery_state: dict[str, Any] | None = None
        if kind == "decision":
            lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
            reply_text = _controller_decision_reply_text(
                project_context=project_context,
                decision_prompt=str(job.get("decision_prompt", "")),
                lang_hint=lang_hint,
            )
        else:
            doc = build_grounded_status_reply_doc(run_dir=run_dir, session_state=session_state, project_context=project_context)
            reply_text = str(doc.get("reply_text", "")).strip()
            provider_status = str(doc.get("provider_status", "executed")).strip() or "executed"
            reply_actions = normalize_actions(doc.get("actions", [])); reply_delivery_state = collect_public_delivery_state(session_state=session_state, project_context=project_context, source="telegram", support_run_dir=run_dir)
            if not reply_text:
                continue
            write_json(run_dir / SUPPORT_REPLY_REL_PATH, doc)
        if kind == "progress":
            lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
            reply_text = _normalize_proactive_progress_reply_text(reply_text, lang_hint=lang_hint)
        if not reply_text:
            continue
        reply_preview_plan = (
            resolve_public_delivery_plan(run_dir=run_dir, actions=reply_actions, delivery_state=reply_delivery_state)
            if reply_actions
            else {}
        )
        lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
        public_reply_text = _prepare_public_reply_for_telegram(
            reply_text,
            delivery_preview=reply_preview_plan,
            lang_hint=lang_hint,
        )
        if not public_reply_text:
            continue
        binding = build_progress_binding(
            project_context=project_context,
            task_summary_hint=current_project_brief(session_state),
        )
        sync_active_task_truth(
            session_state,
            user_text="现在做到什么程度了",
            source="telegram_auto_resume",
            conversation_mode="STATUS_QUERY",
            frontdesk_state=current_frontdesk_state(session_state),
            project_context=project_context,
            delivery_state=collect_public_delivery_state(
                session_state=session_state,
                project_context=project_context,
                source="telegram",
                support_run_dir=run_dir,
            ),
            provider_result={"status": provider_status, "reason": str(job.get("reason", ""))},
            assistant_reply_text="",
            rewrite_latest_user_turn=False,
        )
        frontdesk_state = current_frontdesk_state(session_state)
        session_state["latest_support_context"] = {
            "run_id": str((project_context or {}).get("run_id", "")),
            "provider_status": provider_status,
            "conversation_mode": "STATUS_QUERY",
            "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80),
            "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80),
            "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
            "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220),
            "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
            "message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
            "frontdesk_state": str(frontdesk_state.get("state", "")),
            "interrupt_kind": str(frontdesk_state.get("interrupt_kind", "")),
            "package_ready": False,
            "package_delivery_mode": "",
            "package_structure_hint": [],
            "screenshot_ready": False,
            "video_ready": False,
        }
        try:
            emit_public_message(tg, chat_id, public_reply_text)
            if reply_actions:
                config, _ = load_dispatch_config(run_dir)
                plan = emit_public_delivery(build_public_delivery_transport(config=config, run_dir=run_dir, live_transport=tg), chat_id=chat_id, run_dir=run_dir, actions=reply_actions, delivery_state=reply_delivery_state)
                if delivery_plan_failed(reply_actions, plan): raise RuntimeError("public delivery action produced no sent files")
        except Exception as exc:
            keep_retrying = _handle_outbound_send_failure_with_limit(
                session_state=session_state,
                job=job,
                kind=kind,
                error_text=str(exc),
            )
            append_event(
                run_dir,
                "SUPPORT_PROGRESS_SEND_FAILED",
                SUPPORT_REPLY_REL_PATH.as_posix(),
                run_id=str((project_context or {}).get("run_id", "")),
                kind=kind,
                reason=str(job.get("reason", "")),
                error=sanitize_inline_text(str(exc), max_chars=220),
            )
            if not keep_retrying:
                append_event(
                    run_dir,
                    "SUPPORT_PROGRESS_SUPPRESSED",
                    SUPPORT_REPLY_REL_PATH.as_posix(),
                    run_id=str((project_context or {}).get("run_id", "")),
                    kind=kind,
                    reason="retry_limit_reached",
                    fail_count=int(job.get("send_fail_count", 0) or 0),
                )
            continue
        sent += 1
        ctcp_support_controller.mark_job_sent(
            session_state,
            job,
            now_ts=now_iso(),
            cooldown_sec=SUPPORT_NOTIFICATION_COOLDOWN_SEC,
        )
        if kind in {"progress", "result", "error"}:
            remember_progress_notification(
                session_state,
                project_context=project_context,
                task_summary_hint=current_project_brief(session_state),
                status_hash=str(job.get("status_hash", "")),
            )
        append_event(
            run_dir,
            "SUPPORT_PROGRESS_PUSHED",
            SUPPORT_REPLY_REL_PATH.as_posix(),
            run_id=str((project_context or {}).get("run_id", "")),
            auto_advanced=auto_advanced,
            recovered=bool(recovered_candidate),
            phase=str(binding.get("current_phase", "")),
            kind=kind,
            reason=str(job.get("reason", "")),
        )
    return sent
def run_proactive_support_cycle(tg: TelegramClient, allowlist: set[int] | None) -> None:
    for chat_id in iter_telegram_support_chat_ids(allowlist):
        run_dir = session_run_dir(chat_id)
        state_path = run_dir / SUPPORT_SESSION_STATE_REL_PATH
        if not state_path.exists():
            continue
        session_state = load_support_session_state(run_dir, str(chat_id))
        bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
        if not bound_run_id:
            continue
        project_context, _ = fetch_support_context_with_recovery(
            run_dir=run_dir,
            session_state=session_state,
            bound_run_id=bound_run_id,
            trigger="proactive_cycle",
        )
        project_context, session_state, recovered_candidate = maybe_recover_previous_outline_context(
            run_dir=run_dir,
            chat_id=str(chat_id),
            user_text="",
            source="telegram_auto_resume",
            conversation_mode="PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
            allow_history_resume=True,
        )
        if not isinstance(project_context, dict):
            continue
        annotate_plan_draft_recovery(project_context, attempted=False)
        auto_advanced = False
        if should_auto_advance_project_context(session_state, project_context):
            bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
            if bound_run_id:
                advance_steps = 4 if is_missing_plan_draft_context(project_context) else 2
                ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=advance_steps)
                latest_notification_state(session_state)["last_auto_advance_ts"] = now_iso()
                project_context, _ = fetch_support_context_with_recovery(
                    run_dir=run_dir,
                    session_state=session_state,
                    bound_run_id=bound_run_id,
                    trigger="proactive_post_advance",
                )
                annotate_plan_draft_recovery(project_context, attempted=True)
                auto_advanced = True
        status_hash, binding = build_progress_digest(
            project_context=project_context,
            task_summary_hint=current_project_brief(session_state),
        )
        if not status_hash:
            if recovered_candidate is not None:
                save_support_session_state(run_dir, session_state)
            continue
        proactive_delivery_state = collect_public_delivery_state(
            session_state=session_state,
            project_context=project_context,
            source="telegram",
            support_run_dir=run_dir,
        )
        proactive_frontdesk_state = sync_frontdesk_state(
            session_state,
            user_text="现在做到什么程度了",
            conversation_mode="STATUS_QUERY",
            project_context=project_context,
            delivery_state=proactive_delivery_state,
            provider_result={"status": "executed", "reason": "proactive_cycle"},
        )
        sync_active_task_truth(
            session_state,
            user_text="现在做到什么程度了",
            source="telegram_auto_resume",
            conversation_mode="STATUS_QUERY",
            frontdesk_state=proactive_frontdesk_state,
            project_context=project_context,
            delivery_state=proactive_delivery_state,
            provider_result={"status": "executed", "reason": "proactive_cycle"},
            assistant_reply_text="",
            rewrite_latest_user_turn=False,
        )
        session_state["latest_support_context"] = {
            "run_id": str((project_context or {}).get("run_id", "")),
            "provider_status": "executed",
            "conversation_mode": "STATUS_QUERY",
            "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80),
            "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80),
            "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
            "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220),
            "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
            "message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
            "frontdesk_state": str(proactive_frontdesk_state.get("state", "")),
            "interrupt_kind": str(proactive_frontdesk_state.get("interrupt_kind", "")),
            "package_ready": bool(proactive_delivery_state.get("package_ready", False)),
            "package_delivery_allowed": bool(proactive_delivery_state.get("package_delivery_allowed", False)),
            "package_blocked_reason": sanitize_inline_text(str(proactive_delivery_state.get("package_blocked_reason", "")), max_chars=120),
            "package_delivery_mode": str(proactive_delivery_state.get("package_delivery_mode", "")).strip(),
            "package_structure_hint": list(proactive_delivery_state.get("package_structure_hint", [])),
            "screenshot_ready": bool(proactive_delivery_state.get("screenshot_ready", False)),
            "video_ready": bool(proactive_delivery_state.get("video_ready", False)),
            "t2p_state": sanitize_inline_text(str(latest_generation_state(session_state).get("current_state", "")), max_chars=32),
            "t2p_pass_fail": sanitize_inline_text(str(latest_generation_state(session_state).get("last_pass_fail", "")), max_chars=12),
            "t2p_failure_stage": sanitize_inline_text(str(latest_generation_state(session_state).get("last_failure_stage", "")), max_chars=40),
            "t2p_report_path": sanitize_inline_text(str(latest_generation_state(session_state).get("last_report_path", "")), max_chars=220),
        }
        ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts=now_iso(),
            keepalive_interval_sec=SUPPORT_EXECUTION_KEEPALIVE_INTERVAL_SEC,
        )
        _ = _emit_controller_outbound_jobs(
            tg=tg,
            chat_id=chat_id,
            run_dir=run_dir,
            session_state=session_state,
            project_context=project_context,
            auto_advanced=auto_advanced,
            recovered_candidate=recovered_candidate,
        )
        save_support_session_state(run_dir, session_state)
def resolve_telegram_token(raw: str) -> str:
    text = str(raw or "").strip()
    if text:
        return text
    for key in ("CTCP_TG_TOKEN", "TELEGRAM_BOT_TOKEN"):
        value = str(os.environ.get(key, "")).strip()
        if value:
            return value
    return ""
def run_stdin_mode(chat_id: str, provider_override: str = "") -> int:
    # 修复Windows编码问题：确保stdin使用UTF-8编码
    stdin_encoding = str(getattr(sys.stdin, "encoding", "") or "").lower()
    if stdin_encoding != "utf-8":
        import io
        stdin_buffer = getattr(sys.stdin, "buffer", None)
        if stdin_buffer is not None:
            try:
                sys.stdin = io.TextIOWrapper(stdin_buffer, encoding="utf-8", errors="replace")
            except Exception:
                pass
    user_text = utf8_clean(sys.stdin.read()).strip()
    if not user_text:
        print("[ctcp_support_bot] stdin message is empty", file=sys.stderr)
        return 1
    doc, _ = process_message(chat_id=chat_id, user_text=user_text, source="stdin", provider_override=provider_override)
    print(str(doc.get("reply_text", "")).strip())
    if formal_api_only_enabled() and bool(doc.get("formal_api_only_failed", False)):
        return 2
    return 0
def _is_telegram_read_timeout(exc: Exception, error_text: str) -> bool:
    low = sanitize_inline_text(error_text, max_chars=320).lower()
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    timeout_markers = (
        "the read operation timed out",
        "read timed out",
        "timed out",
        "timeout",
    )
    return any(marker in low for marker in timeout_markers)
def _should_log_timeout_streak(streak: int) -> bool:
    return streak in {5, 10} or (streak > 0 and (streak % 20 == 0))
def run_telegram_mode(
    token: str,
    poll_seconds: int,
    allowlist_raw: str,
    provider_override: str = "",
    clear_history_on_start: bool = True,
) -> int:
    try:
        lock_path, lock_fh = acquire_telegram_poll_lock(token)
    except Exception as exc:
        print(f"[ctcp_support_bot] {exc}", file=sys.stderr)
        return 2
    try:
        if clear_history_on_start:
            cleanup = clear_telegram_support_history()
            print(
                "[ctcp_support_bot] telegram startup cleared support history: "
                f"count={int(cleanup.get('cleared_count', 0) or 0)} root={cleanup.get('sessions_root', '')}",
                file=sys.stderr,
            )
            if cleanup.get("failed"):
                print(f"[ctcp_support_bot] telegram history cleanup warnings: {cleanup.get('failed')}", file=sys.stderr)
        tg = TelegramClient(token=token, timeout_sec=poll_seconds)
        allowlist = parse_allowlist(allowlist_raw)
        try:
            tg.clear_webhook(drop_pending_updates=clear_history_on_start)
        except Exception as exc:
            print(f"[ctcp_support_bot] telegram deleteWebhook warning: {exc}", file=sys.stderr)
        offset = 0
        get_updates_error_streak = 0
        last_get_updates_error = ""
        while True:
            try:
                updates = tg.get_updates(offset)
                get_updates_error_streak = 0
                last_get_updates_error = ""
            except Exception as exc:
                error_text = sanitize_inline_text(str(exc), max_chars=320)
                get_updates_error_streak += 1
                previous_error = last_get_updates_error
                low = error_text.lower()
                timeout_like = _is_telegram_read_timeout(exc, error_text)
                if timeout_like:
                    if _should_log_timeout_streak(get_updates_error_streak):
                        print(
                            f"[ctcp_support_bot] telegram getUpdates timeout (streak={get_updates_error_streak}): {error_text}",
                            file=sys.stderr,
                        )
                    time.sleep(min(2.0, 0.3 + 0.1 * get_updates_error_streak))
                    try:
                        run_proactive_support_cycle(tg, allowlist)
                    except Exception as proactive_exc:
                        print(f"[ctcp_support_bot] proactive progress error: {proactive_exc}", file=sys.stderr)
                    last_get_updates_error = error_text
                    continue
                should_log = (
                    (error_text != previous_error)
                    or get_updates_error_streak in {1, 2, 3, 5, 10}
                    or (get_updates_error_streak % 20 == 0)
                )
                if should_log:
                    print(
                        f"[ctcp_support_bot] telegram getUpdates error (streak={get_updates_error_streak}): {error_text}",
                        file=sys.stderr,
                    )
                last_get_updates_error = error_text
                if "409" in low and "conflict" in low:
                    try:
                        tg.clear_webhook(drop_pending_updates=False)
                    except Exception:
                        pass
                    if get_updates_error_streak >= 3:
                        print(
                            "[ctcp_support_bot] persistent 409 conflict: another polling client may still be using this token.",
                            file=sys.stderr,
                        )
                time.sleep(min(8.0, 1.0 + 0.3 * get_updates_error_streak))
                continue
            if not updates:
                try:
                    run_proactive_support_cycle(tg, allowlist)
                except Exception as exc:
                    print(f"[ctcp_support_bot] proactive progress error: {exc}", file=sys.stderr)
                continue
            for upd in updates:
                try:
                    uid = int(upd.get("update_id", 0))
                    if uid >= offset:
                        offset = uid + 1
                    msg = upd.get("message", {})
                    if not isinstance(msg, dict):
                        continue
                    chat = msg.get("chat", {})
                    if not isinstance(chat, dict):
                        continue
                    chat_id = int(chat.get("id", 0))
                    if not chat_id:
                        continue
                    if allowlist is not None and chat_id not in allowlist:
                        continue
                    user_text = str(msg.get("text", "")).strip()
                    if not user_text:
                        continue
                    if user_text.startswith("/start"):
                        emit_public_message(
                            tg,
                            chat_id,
                            "欢迎使用 CTCP Support Bot。你把这轮最想推进的目标发我，我现在就开始处理。",
                        )
                        continue
                    doc, support_run_dir = process_message(
                        chat_id=str(chat_id),
                        user_text=user_text,
                        source="telegram",
                        provider_override=provider_override,
                    )
                    session_state = load_support_session_state(support_run_dir, str(chat_id))
                    project_context: dict[str, Any] | None = None
                    bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
                    if bound_run_id:
                        try:
                            fetched, _ = fetch_support_context_with_recovery(
                                run_dir=support_run_dir,
                                session_state=session_state,
                                bound_run_id=bound_run_id,
                                trigger="telegram_post_reply",
                            )
                            if isinstance(fetched, dict):
                                project_context = fetched
                        except Exception:
                            project_context = None
                    delivery_state = collect_public_delivery_state(
                        session_state=session_state,
                        project_context=project_context,
                        source="telegram",
                        support_run_dir=support_run_dir,
                    )
                    reply_actions = list(doc.get("actions", []) or [])
                    reply_preview_plan = resolve_public_delivery_plan(
                        run_dir=support_run_dir,
                        actions=reply_actions,
                        delivery_state=delivery_state,
                    )
                    lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
                    public_reply_text = _prepare_public_reply_for_telegram(
                        str(doc.get("reply_text", "")).strip(),
                        delivery_preview=reply_preview_plan,
                        lang_hint=lang_hint,
                    )
                    if public_reply_text:
                        emit_public_message(tg, chat_id, public_reply_text)
                    config, _ = load_dispatch_config(support_run_dir)
                    plan = emit_public_delivery(
                        build_public_delivery_transport(config=config, run_dir=support_run_dir, live_transport=tg),
                        chat_id=chat_id,
                        run_dir=support_run_dir,
                        actions=reply_actions,
                        delivery_state=delivery_state,
                    )
                    if delivery_plan_failed(reply_actions, plan):
                        emit_public_message(tg, chat_id, "交付文件发送失败：我没有把 zip 或截图成功发出，后台会保留失败记录并等待下一次重试。")
                except Exception as exc:
                    print(f"[ctcp_support_bot] telegram update error: {exc}", file=sys.stderr)
                    continue
    finally:
        release_telegram_poll_lock(lock_path, lock_fh)
def run_selftest() -> int:
    chat_id = f"selftest-{int(time.time())}"
    message = "请帮我像 CEO 一样安排客服推进节奏。"
    doc, run_dir = process_message(
        chat_id=chat_id,
        user_text=message,
        source="selftest",
        provider_override="ollama_agent",
    )
    reply_path = run_dir / SUPPORT_REPLY_REL_PATH
    if not reply_path.exists():
        raise AssertionError(f"missing {reply_path}")
    payload = read_json_doc(reply_path)
    if payload is None:
        raise AssertionError("support_reply.json is not valid json object")
    for key in ("reply_text", "next_question", "actions"):
        if key not in payload:
            raise AssertionError(f"missing key: {key}")
    reply_text = str(payload.get("reply_text", ""))
    lower = reply_text.lower()
    banned = ("trace", "logs/", "logs\\", "outbox/", "outbox\\", "diff --git")
    for token in banned:
        if token in lower:
            raise AssertionError(f"reply_text contains forbidden token: {token}")
    print(f"[ctcp_support_bot][selftest] PASS run_dir={run_dir}")
    print(f"[ctcp_support_bot][selftest] reply={sanitize_inline_text(str(doc.get('reply_text', '')), max_chars=200)}")
    return 0
def main() -> int:
    ap = argparse.ArgumentParser(description="CTCP Support Bot (dual-channel customer output + run_dir logs)")
    ap.add_argument("--stdin", action="store_true", help="Read one user message from stdin and print reply_text to stdout")
    ap.add_argument("--chat-id", default="stdin", help="Session id used with --stdin mode")
    ap.add_argument("--selftest", action="store_true", help="Run selftest using model-only support reply path")
    ap.add_argument("--provider", default="", help="Optional provider override for support_lead")
    sub = ap.add_subparsers(dest="mode")
    p_tg = sub.add_parser("telegram", help="Run Telegram long-poll loop")
    p_tg.add_argument("--token", default="", help="Telegram bot token (or use CTCP_TG_TOKEN / TELEGRAM_BOT_TOKEN)")
    p_tg.add_argument("--poll-seconds", type=int, default=2, help="Telegram long-poll timeout seconds")
    p_tg.add_argument("--allowlist", default="", help="Optional chat id allowlist: id1,id2")
    p_tg.add_argument("--keep-history", action="store_true", help="Do not clear local support sessions or pending updates on startup")
    args = ap.parse_args()
    override = str(args.provider or "").strip()
    if args.selftest:
        return run_selftest()
    if bool(args.stdin):
        return run_stdin_mode(chat_id=str(args.chat_id), provider_override=override)
    if args.mode == "telegram":
        token = resolve_telegram_token(str(args.token))
        if not token:
            print("[ctcp_support_bot] telegram token missing; pass --token or set CTCP_TG_TOKEN", file=sys.stderr)
            return 1
        return run_telegram_mode(
            token=token,
            poll_seconds=int(args.poll_seconds),
            allowlist_raw=str(args.allowlist),
            provider_override=override,
            clear_history_on_start=not bool(args.keep_history),
        )
    ap.print_help()
    return 1
if __name__ == "__main__":
    raise SystemExit(main())
