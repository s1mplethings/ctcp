from __future__ import annotations

from typing import Any, Mapping

def _clean(text: Any, *, limit: int) -> str:
    value = str(text or "").strip()
    return value[:limit]


def latest_known_project_goal(session_state: Mapping[str, Any]) -> str:
    project_memory = session_state.get("project_memory", {})
    latest_support_context = session_state.get("latest_support_context", {})
    if not isinstance(project_memory, Mapping):
        project_memory = {}
    if not isinstance(latest_support_context, Mapping):
        latest_support_context = {}
    return _clean(
        project_memory.get("project_brief", "")
        or session_state.get("task_summary", "")
        or session_state.get("active_goal", "")
        or latest_support_context.get("goal", ""),
        limit=280,
    )


def is_missing_plan_draft_context(project_context: Mapping[str, Any] | None) -> bool:
    if not isinstance(project_context, Mapping):
        return False
    runtime_state = project_context.get("runtime_state", {})
    status = project_context.get("status", {})
    if not isinstance(runtime_state, Mapping):
        runtime_state = {}
    if not isinstance(status, Mapping):
        status = {}
    gate = runtime_state.get("gate", {})
    if (not isinstance(gate, Mapping)) or (not gate):
        gate = status.get("gate", {})
    if not isinstance(gate, Mapping):
        gate = {}
    path = _clean(gate.get("path", ""), limit=180).lower()
    reason = _clean(runtime_state.get("blocking_reason", "") or gate.get("reason", ""), limit=220).lower()
    return "plan_draft.md" in path or "plan_draft.md" in reason


def is_auto_advance_pipeline_block_context(project_context: Mapping[str, Any] | None) -> bool:
    if not isinstance(project_context, Mapping):
        return False
    runtime_state = project_context.get("runtime_state", {})
    status = project_context.get("status", {})
    if not isinstance(runtime_state, Mapping):
        runtime_state = {}
    if not isinstance(status, Mapping):
        status = {}
    gate = runtime_state.get("gate", {})
    if (not isinstance(gate, Mapping)) or (not gate):
        gate = status.get("gate", {})
    if not isinstance(gate, Mapping):
        gate = {}
    path = _clean(gate.get("path", ""), limit=180).lower()
    reason = _clean(runtime_state.get("blocking_reason", "") or gate.get("reason", ""), limit=220).lower()
    return any(
        marker in path or marker in reason
        for marker in ("file_request.json", "context_pack.json", "plan_draft.md")
    )


def plan_draft_recovery_hint(*, attempted: bool) -> str:
    if attempted:
        return "已重试一次方案整理；接下来继续补齐 PLAN_draft.md，若仍缺失就转入明确恢复状态"
    return "我会先重试方案整理，补齐 PLAN_draft.md；如果继续缺失就转入明确恢复状态"


def annotate_plan_draft_recovery(project_context: dict[str, Any] | None, *, attempted: bool) -> None:
    if not isinstance(project_context, dict) or not is_missing_plan_draft_context(project_context):
        return
    runtime_state = project_context.get("runtime_state", {})
    if not isinstance(runtime_state, dict):
        runtime_state = {}
    runtime_recovery = runtime_state.get("recovery", {})
    if not isinstance(runtime_recovery, dict):
        runtime_recovery = {}
    explicit_status = _clean(runtime_recovery.get("status", ""), limit=40).lower()
    if explicit_status in {"recovery_needed", "exec_failed", "blocked_hard"}:
        project_context["support_recovery"] = dict(runtime_recovery)
        return
    support_recovery = project_context.get("support_recovery", {})
    if not isinstance(support_recovery, dict):
        support_recovery = {}
    support_recovery["needed"] = True
    support_recovery["status"] = "retrying" if attempted else "retry_ready"
    support_recovery["hint"] = plan_draft_recovery_hint(attempted=attempted)
    support_recovery["last_attempt"] = "已重试一次方案整理" if attempted else ""
    project_context["support_recovery"] = support_recovery


def stale_bound_run_recovery_hint(goal: str) -> str:
    if goal:
        return "我已经清掉失效的 run 绑定；你回复“继续”或补充要求后，我会按当前项目目标重新绑定一个新 run 再继续推进"
    return "我已经清掉失效的 run 绑定；你把当前要继续的项目目标再发我一次，我就重新绑定并继续推进"


def build_stale_bound_run_context(*, session_state: Mapping[str, Any], stale_run_id: str, error_text: str) -> dict[str, Any]:
    goal = latest_known_project_goal(session_state)
    blocker = _clean(error_text or f"run_id not found: {stale_run_id}", limit=220)
    recovery_hint = stale_bound_run_recovery_hint(goal)
    gate = {
        "state": "blocked",
        "owner": "support_session",
        "path": "",
        "reason": blocker,
    }
    runtime_state = {
        "phase": "RECOVER",
        "run_status": "blocked",
        "blocking_reason": blocker,
        "needs_user_decision": False,
        "decisions_needed_count": 0,
        "gate": gate,
        "error": {"has_error": True, "code": "missing_bound_run", "message": blocker},
        "recovery": {
            "needed": True,
            "hint": recovery_hint,
            "status": "required",
            "last_attempt": "已清理失效 run 绑定",
            "last_invalid_run_id": _clean(stale_run_id, limit=80),
        },
    }
    return {
        "run_id": "",
        "run_dir": "",
        "goal": goal,
        "status": {
            "run_status": "blocked",
            "verify_result": "",
            "needs_user_decision": False,
            "decisions_needed_count": 0,
            "blocking_reason": blocker,
            "gate": gate,
        },
        "runtime_state": runtime_state,
        "decisions": {"count": 0, "decisions": []},
        "whiteboard": {},
        "support_recovery": dict(runtime_state.get("recovery", {})),
        "error": blocker,
    }


def resolve_new_run_goal(
    *,
    user_text: str,
    conversation_mode: str,
    session_state: Mapping[str, Any],
    should_refresh_project_brief: Any,
    is_low_signal_project_followup: Any,
    is_project_execution_followup: Any,
) -> str:
    mode = _clean(conversation_mode, limit=40).upper()
    raw = _clean(user_text, limit=280)
    existing_goal = latest_known_project_goal(session_state)
    if should_refresh_project_brief(raw, mode):
        return raw
    if mode == "STATUS_QUERY":
        return ""
    if existing_goal and (
        is_low_signal_project_followup(raw)
        or is_project_execution_followup(raw)
        or mode in {"PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}
    ):
        return existing_goal
    if raw and not is_low_signal_project_followup(raw):
        return raw
    return ""

def runtime_phase_to_support_stage(phase: str) -> str:
    mapping = {
        "INTAKE": "INTAKE",
        "CLARIFY": "CLARIFY",
        "PLAN": "PLAN",
        "EXECUTE": "EXECUTE",
        "VERIFY": "VERIFY",
        "RETRYING": "RETRYING",
        "RECOVERY_NEEDED": "RECOVERY_NEEDED",
        "EXEC_FAILED": "EXEC_FAILED",
        "BLOCKED_HARD": "BLOCKED_HARD",
        "WAIT_USER_DECISION": "WAIT_USER_DECISION",
        "FINALIZE": "FINALIZE",
        "DELIVER": "DELIVER",
        "DELIVERED": "DELIVERED",
        "RECOVER": "RECOVER",
    }
    return mapping.get(_clean(phase, limit=40).upper(), "")

def authoritative_stage_for_runtime(
    *,
    runtime_phase: str,
    session_stage: str,
    run_status: str,
    verify_result: str,
    needs_user_decision: bool,
    final_ready_statuses: set[str],
) -> str:
    phase = _clean(runtime_phase, limit=40).upper()
    runtime_mapping = {
        "INTAKE": "INTAKE",
        "CLARIFY": "PLANNING",
        "PLAN": "PLANNING",
        "EXECUTE": "EXECUTING",
        "VERIFY": "VERIFYING",
        "RETRYING": "BLOCKED",
        "RECOVERY_NEEDED": "BLOCKED",
        "BLOCKED_HARD": "BLOCKED",
        "EXEC_FAILED": "FAILED",
        "WAIT_USER_DECISION": "WAITING_DECISION",
        "FINALIZE": "VERIFYING",
        "DELIVER": "DONE",
        "DELIVERED": "DONE",
        "RECOVER": "BLOCKED",
    }
    if phase in runtime_mapping:
        return runtime_mapping[phase]
    if _clean(verify_result, limit=16).upper() == "PASS" and _clean(run_status, limit=24).lower() in final_ready_statuses:
        return "DONE"
    if needs_user_decision:
        return "WAITING_DECISION"
    if _clean(run_status, limit=24).lower() in {"blocked"}:
        return "BLOCKED"
    if _clean(run_status, limit=24).lower() in {"fail", "failed", "error"}:
        return "FAILED"
    stage = _clean(session_stage, limit=24).upper()
    mapping = {
        "INTAKE": "INTAKE",
        "CLARIFY": "PLANNING",
        "PLAN": "PLANNING",
        "EXECUTE": "EXECUTING",
        "VERIFY": "VERIFYING",
        "RETRYING": "BLOCKED",
        "RECOVERY_NEEDED": "BLOCKED",
        "BLOCKED_HARD": "BLOCKED",
        "EXEC_FAILED": "FAILED",
        "WAIT_USER_DECISION": "WAITING_DECISION",
        "FINALIZE": "VERIFYING",
        "DELIVER": "DONE",
        "DELIVERED": "DONE",
        "RECOVER": "BLOCKED",
        "ERROR": "FAILED",
    }
    if stage in mapping:
        return mapping[stage]
    if _clean(run_status, limit=24).lower() in {"running", "in_progress", "working"}:
        return "EXECUTING"
    return "NEW"

def should_auto_advance_project_context(
    project_context: Mapping[str, Any] | None,
    *,
    last_auto_advance_ts: str,
    interval_sec: int,
    seconds_since: Any,
) -> bool:
    if not isinstance(project_context, Mapping):
        return False
    runtime_state = project_context.get("runtime_state", {})
    status = project_context.get("status", {})
    if not isinstance(runtime_state, Mapping) or not isinstance(status, Mapping):
        return False
    gate = runtime_state.get("gate", {}) if isinstance(runtime_state.get("gate", {}), Mapping) else {}
    if not gate:
        gate = status.get("gate", {}) if isinstance(status.get("gate", {}), Mapping) else {}
    if not isinstance(gate, Mapping):
        gate = {}
    run_status = _clean(status.get("run_status", ""), limit=24).lower()
    verify_result = _clean(status.get("verify_result", ""), limit=16).upper()
    gate_state = _clean(gate.get("state", ""), limit=40).lower()
    runtime_phase = _clean(runtime_state.get("phase", ""), limit=40).upper()
    recovery = runtime_state.get("recovery", {}) if isinstance(runtime_state.get("recovery", {}), Mapping) else {}
    recovery_status = _clean(recovery.get("status", ""), limit=40).lower()
    if verify_result == "PASS" or run_status in {"pass", "done", "completed", "fail", "failed", "error"}:
        return False
    if runtime_phase in {"RECOVERY_NEEDED", "EXEC_FAILED", "BLOCKED_HARD"} or recovery_status in {"recovery_needed", "exec_failed", "blocked_hard"}:
        return False
    if bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0:
        return False
    retry_ready = recovery_status == "retry_ready" or _clean(gate.get("watchdog_status", ""), limit=40).lower() == "retry_ready"
    recoverable_pipeline_block = gate_state == "blocked" and (retry_ready or is_auto_advance_pipeline_block_context(project_context))
    if gate_state == "blocked" and not recoverable_pipeline_block:
        return False
    elapsed = seconds_since(str(last_auto_advance_ts or ""))
    if elapsed is not None and elapsed < max(0, int(interval_sec or 0)):
        return False
    return (
        run_status in {"running", "in_progress", "working"}
        or gate_state in {"", "open", "ready"}
        or retry_ready
        or recoverable_pipeline_block
    )


def build_frontend_backend_truth_state(
    *,
    provider_result: Mapping[str, Any],
    raw_doc: Mapping[str, Any],
    project_context: Mapping[str, Any] | None,
    conversation_mode: str,
    has_user_msgs: bool,
    task_summary_hint: str,
    build_progress_binding: Any,
) -> dict[str, Any]:
    status_text = _clean(provider_result.get("status", ""), limit=80).lower()
    reason_text = _clean(provider_result.get("reason", ""), limit=240)
    raw_reply_text = _clean(raw_doc.get("reply_text", ""), limit=400)
    is_executed = status_text == "executed"
    is_deferred = status_text in {"outbox_created", "outbox_exists", "pending", "deferred"}
    is_hard_failure = status_text in {"exec_failed", "failed", "error"} or any(
        token in reason_text.lower() for token in ("traceback", "stack trace", "command failed", "exception")
    )
    if is_executed:
        stage = "support_provider_executed"
    elif is_deferred:
        stage = "support_provider_deferred"
    else:
        stage = "support_provider_failed"

    backend_state: dict[str, Any] = {
        "stage": stage,
        "run_status": "",
        "reason": reason_text,
        "missing_fields": raw_doc.get("missing_fields", []),
        "blocked_needs_input": bool(is_hard_failure),
        "needs_input": bool(_clean(raw_doc.get("next_question", ""), limit=240)) or bool(is_hard_failure),
        "has_actionable_goal": has_user_msgs,
        "first_pass_understood": has_user_msgs,
        "reply_truth_status": "",
        "reply_truth_reason": reason_text,
        "reply_truth_next_action": "",
        "reply_source_confidence": "low" if _clean(provider_result.get("degraded_from", ""), limit=80) else "high",
    }
    if is_hard_failure:
        backend_state["reply_truth_status"] = "backend_unavailable"
    elif is_deferred or (is_executed and not raw_reply_text):
        backend_state["reply_truth_status"] = "backend_deferred"
    elif _clean(provider_result.get("degraded_from", ""), limit=80):
        backend_state["reply_truth_status"] = "low_confidence_fallback"

    if not isinstance(project_context, Mapping):
        return backend_state

    status = project_context.get("status", {})
    if not isinstance(status, Mapping):
        return backend_state
    gate = status.get("gate", {})
    if not isinstance(gate, Mapping):
        gate = {}
    decisions = project_context.get("decisions", {})
    if not isinstance(decisions, Mapping):
        decisions = {}

    run_status = _clean(status.get("run_status", ""), limit=60).lower()
    verify_result = _clean(status.get("verify_result", ""), limit=32).upper()
    gate_state = _clean(gate.get("state", ""), limit=40).lower()
    decision_count = int(status.get("decisions_needed_count", decisions.get("count", 0) or 0) or 0)
    waiting_for_decision = decision_count > 0
    gate_blocked_on_internal = gate_state == "blocked" and not waiting_for_decision
    gate_blocked_on_user = gate_state == "blocked" and waiting_for_decision

    if verify_result == "PASS" or run_status in {"pass", "done", "completed"}:
        stage = "done"
    elif waiting_for_decision:
        stage = "decision_needed"
    elif gate_blocked_on_user:
        stage = "advance_blocked"
    elif gate_blocked_on_internal:
        stage = "executing"
    elif _clean(conversation_mode, limit=40).upper() == "STATUS_QUERY":
        stage = "status_reply"
    elif run_status in {"running", "in_progress", "working"}:
        stage = "executing"
    elif project_context.get("advance"):
        stage = "advance_success"
    else:
        stage = backend_state["stage"]

    backend_state.update(
        {
            "stage": stage,
            "run_status": run_status,
            "verify_result": verify_result,
            "reason": _clean(gate.get("reason", ""), limit=240) or reason_text,
            "waiting_for_decision": waiting_for_decision,
            "decisions_count": decision_count,
            "needs_input": waiting_for_decision or gate_blocked_on_user,
            "blocked_needs_input": gate_blocked_on_user,
            "has_actionable_goal": True,
            "first_pass_understood": True,
            "progress_binding": build_progress_binding(
                project_context=project_context,
                task_summary_hint=task_summary_hint,
            ),
        }
    )
    if gate_blocked_on_internal:
        backend_state["reply_truth_status"] = "backend_blocked"
        backend_state["reply_truth_reason"] = _clean(gate.get("reason", ""), limit=240) or _clean(status.get("blocking_reason", ""), limit=240) or reason_text
        recovery = project_context.get("support_recovery", {})
        if not isinstance(recovery, Mapping):
            recovery = {}
        runtime_state = project_context.get("runtime_state", {})
        if isinstance(runtime_state, Mapping):
            runtime_recovery = runtime_state.get("recovery", {})
            if isinstance(runtime_recovery, Mapping) and runtime_recovery:
                recovery = runtime_recovery
        backend_state["reply_truth_next_action"] = _clean(recovery.get("hint", ""), limit=240) or _clean(recovery.get("last_attempt", ""), limit=240)
    elif run_status in {"failed", "error", "aborted"}:
        backend_state["reply_truth_status"] = "backend_failed"
        backend_state["reply_truth_reason"] = _clean(gate.get("reason", ""), limit=240) or reason_text
    return backend_state


def inject_provider_truth_context(
    *,
    project_context: Mapping[str, Any] | None,
    provider_result: Mapping[str, Any],
    raw_doc: Mapping[str, Any],
) -> dict[str, Any]:
    policy_project_context = dict(project_context or {})
    truth_status = ""
    truth_reason = ""
    truth_next_action = ""
    truth_confidence = "high"
    degraded_from = _clean(provider_result.get("degraded_from", ""), limit=80)
    degraded_reason = _clean(provider_result.get("degraded_reason", ""), limit=240)
    degraded_kind = _clean(provider_result.get("degraded_kind", ""), limit=80)
    provider_status = _clean(provider_result.get("status", ""), limit=60).lower()
    if degraded_from:
        truth_status = "low_confidence_fallback"
        truth_reason = degraded_reason or degraded_kind or _clean(provider_result.get("reason", ""), limit=240)
        truth_confidence = "low"
    elif provider_status in {"exec_failed", "failed", "error"}:
        truth_status = "backend_unavailable"
        truth_reason = _clean(provider_result.get("reason", ""), limit=240)
    elif provider_status in {"outbox_created", "outbox_exists", "pending", "deferred"} or not _clean(raw_doc.get("reply_text", ""), limit=400):
        truth_status = "backend_deferred"
        truth_reason = _clean(provider_result.get("reason", ""), limit=240)
    if truth_status:
        policy_project_context["support_reply_truth"] = {
            "reply_truth_status": truth_status,
            "reply_truth_reason": truth_reason,
            "reply_truth_next_action": truth_next_action,
            "reply_source_confidence": truth_confidence,
        }
    return policy_project_context
