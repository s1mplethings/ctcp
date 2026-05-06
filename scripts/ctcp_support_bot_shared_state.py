#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from scripts.ctcp_support_bot_constants import _FINAL_READY_RUN_STATUSES
from scripts.ctcp_support_bot_io import append_log, now_iso, session_run_dir
from scripts.ctcp_support_bot_progress import build_progress_binding
from scripts.ctcp_support_bot_reply_utils import sanitize_inline_text
from scripts.ctcp_support_bot_session_state import current_project_brief
from scripts.ctcp_support_bot_state_sync import _project_runtime_state
from scripts.ctcp_support_recovery import authoritative_stage_for_runtime as authoritative_stage_for_runtime_impl

try:
    from bridge.state_store import SharedStateStore
except Exception:
    SharedStateStore = None  # type: ignore[assignment]


def _shared_task_id(
    *,
    chat_id: str,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
) -> str:
    run_id = sanitize_inline_text(str((project_context or {}).get("run_id", "")), max_chars=80)
    if run_id:
        return run_id
    active_task_id = sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80)
    if active_task_id:
        return active_task_id
    safe_chat = sanitize_inline_text(chat_id, max_chars=80)
    return f"support-{safe_chat}" if safe_chat else ""


def _to_authoritative_stage(
    *,
    runtime_phase: str,
    session_stage: str,
    run_status: str,
    verify_result: str,
    needs_user_decision: bool,
) -> str:
    return authoritative_stage_for_runtime_impl(
        runtime_phase=runtime_phase,
        session_stage=session_stage,
        run_status=run_status,
        verify_result=verify_result,
        needs_user_decision=needs_user_decision,
        final_ready_statuses=_FINAL_READY_RUN_STATUSES,
    )


def sync_shared_state_workspace(
    *,
    chat_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
) -> dict[str, Any]:
    _ = frontdesk_state
    if SharedStateStore is None:
        return {}
    try:
        store = SharedStateStore()
    except Exception:
        return {}
    task_id = _shared_task_id(chat_id=chat_id, session_state=session_state, project_context=project_context)
    if not task_id:
        return {}
    status = (project_context or {}).get("status", {}) if isinstance(project_context, dict) else {}
    if not isinstance(status, dict):
        status = {}
    runtime_state = _project_runtime_state(project_context)
    run_status, verify_result, needs_user_decision = _runtime_status_triplet(status=status, runtime_state=runtime_state)
    progress = build_progress_binding(
        project_context=project_context if isinstance(project_context, dict) else None,
        task_summary_hint=current_project_brief(session_state),
    )
    authoritative_stage = _to_authoritative_stage(
        runtime_phase=sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40),
        session_stage=str(session_state.get("active_stage", "")),
        run_status=run_status,
        verify_result=verify_result,
        needs_user_decision=needs_user_decision,
    )
    runtime_payload = _runtime_payload(progress=progress, conversation_mode=conversation_mode)
    try:
        _append_shared_state_events(
            store=store,
            task_id=task_id,
            user_text=user_text,
            source=source,
            conversation_mode=conversation_mode,
            session_state=session_state,
            authoritative_stage=authoritative_stage,
            run_status=run_status,
            status=status,
            verify_result=verify_result,
            runtime_payload=runtime_payload,
        )
        current = store.rebuild_current(task_id)
        render = store.refresh_render(task_id, source="runtime", emit_event=True)
        return {"task_id": task_id, "current": current, "render": render, "workspace_root": str(store.workspace_root)}
    except Exception as exc:
        append_log(session_run_dir(chat_id) / "logs" / "support_bot.debug.log", f"[{now_iso()}] shared state sync failed: {exc}\n")
        return {}


def _runtime_status_triplet(*, status: dict[str, Any], runtime_state: dict[str, Any]) -> tuple[str, str, bool]:
    run_status = sanitize_inline_text(str(status.get("run_status", "")), max_chars=24).lower()
    verify_result = sanitize_inline_text(str(status.get("verify_result", "")), max_chars=16).upper()
    if not run_status:
        run_status = sanitize_inline_text(str(runtime_state.get("run_status", "")), max_chars=24).lower()
    if not verify_result:
        verify_result = sanitize_inline_text(str(runtime_state.get("verify_result", "")), max_chars=16).upper()
    needs_user_decision = bool(runtime_state.get("needs_user_decision", False))
    if not needs_user_decision:
        needs_user_decision = bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0
    return run_status, verify_result, needs_user_decision


def _runtime_payload(*, progress: dict[str, Any], conversation_mode: str) -> dict[str, Any]:
    return {
        "current_task_goal": sanitize_inline_text(str(progress.get("current_task_goal", "")), max_chars=260),
        "last_confirmed_items": list(progress.get("last_confirmed_items", [])) if isinstance(progress.get("last_confirmed_items", []), list) else [],
        "current_blocker": sanitize_inline_text(str(progress.get("current_blocker", "none")), max_chars=220),
        "blocking_question": sanitize_inline_text(str(progress.get("blocking_question", "")), max_chars=220),
        "next_action": sanitize_inline_text(str(progress.get("next_action", "")), max_chars=220),
        "proof_refs": list(progress.get("proof_refs", [])) if isinstance(progress.get("proof_refs", []), list) else [],
        "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
    }


def _append_shared_state_events(
    *,
    store: Any,
    task_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
    authoritative_stage: str,
    run_status: str,
    status: dict[str, Any],
    verify_result: str,
    runtime_payload: dict[str, Any],
) -> None:
    frontend_source = "frontdesk" if str(source or "").strip().lower() in {"telegram", "stdin", "selftest"} else "frontend"
    store.append_event(
        task_id=task_id,
        event_type="user_message",
        source=frontend_source,
        payload={
            "text": sanitize_inline_text(user_text, max_chars=600),
            "current_task_goal": sanitize_inline_text(str(session_state.get("active_goal", "")), max_chars=260),
        },
    )
    store.append_event(
        task_id=task_id,
        event_type="conversation_mode_detected",
        source=frontend_source,
        payload={"conversation_mode_guess": sanitize_inline_text(conversation_mode, max_chars=40)},
    )
    if str(conversation_mode or "").strip().upper() == "PROJECT_DECISION_REPLY":
        store.append_event(
            task_id=task_id,
            event_type="user_decision_recorded",
            source=frontend_source,
            payload={"user_decision": sanitize_inline_text(user_text, max_chars=280)},
        )
    store.append_event(
        task_id=task_id,
        event_type="authoritative_stage_changed",
        source="runtime",
        payload={
            "authoritative_stage": authoritative_stage,
            "execution_status": run_status or sanitize_inline_text(str(status.get("gate", "")), max_chars=24),
        },
    )
    for event_type, payload in (
        ("runtime_progress_recorded", runtime_payload),
        (
            "blocker_changed",
            {
                "current_blocker": runtime_payload["current_blocker"] or "none",
                "blocking_question": runtime_payload["blocking_question"],
            },
        ),
        ("next_action_set", {"next_action": runtime_payload["next_action"] or "继续推进当前任务"}),
    ):
        store.append_event(task_id=task_id, event_type=event_type, source="runtime", payload=payload)
    if verify_result:
        store.append_event(
            task_id=task_id,
            event_type="verification_result_recorded",
            source="runtime",
            payload={"verify_result": verify_result, "proof_refs": runtime_payload["proof_refs"]},
        )


__all__ = [
    "_shared_task_id",
    "_to_authoritative_stage",
    "sync_shared_state_workspace",
]
