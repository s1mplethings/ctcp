#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_io import clean_json_value, now_iso, seconds_since
from scripts.ctcp_support_bot_session_state import latest_notification_state
from scripts.ctcp_support_recovery import (
    is_missing_plan_draft_context,
    plan_draft_recovery_hint,
    runtime_phase_to_support_stage as runtime_phase_to_support_stage_impl,
    should_auto_advance_project_context as should_auto_advance_project_context_impl,
)


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def sanitize_inline_text(text: str, max_chars: int = 220) -> str:
    module = _support_bot_host_module()
    candidate = getattr(module, "sanitize_inline_text", None) if module is not None else None
    if callable(candidate):
        return candidate(text, max_chars=max_chars)
    raw = re.sub(r"```[\s\S]*?```", " ", str(text or ""))
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:max_chars].rstrip() if len(raw) > max_chars else raw


def _project_runtime_state(project_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    runtime_state = project_context.get("runtime_state", {})
    return runtime_state if isinstance(runtime_state, dict) else {}


def _runtime_phase_to_support_stage(phase: str) -> str:
    return runtime_phase_to_support_stage_impl(phase)


def _progress_step_label(*, action: str = "", target_path: str = "", role: str = "", reason: str = "") -> str:
    action_l = str(action or "").strip().lower()
    path_l = str(target_path or "").strip().lower()
    role_l = str(role or "").strip().lower()
    reason_l = str(reason or "").strip().lower()
    if "review_contract" in action_l or "review_contract" in path_l or "review_contract" in reason_l or "contract" in role_l:
        return "合同评审"
    if "review_cost" in action_l or "review_cost" in path_l or "review_cost" in reason_l or "cost" in role_l:
        return "成本评审"
    if "lookup" in action_l or "context_pack" in path_l or "librarian" in role_l:
        return "资料检索"
    if "analysis" in action_l or "analysis.md" in path_l:
        return "需求分析"
    if "plan" in action_l or "plan" in path_l:
        return "方案整理"
    if "patch" in action_l or "diff.patch" in path_l:
        return "实现修复"
    if "verify" in action_l or "verify" in path_l or "verifier" in role_l:
        return "验收检查"
    return ""


def _append_progress_item(items: list[str], text: str, *, limit: int = 3) -> None:
    normalized = sanitize_inline_text(text, max_chars=120)
    if normalized and normalized not in items and len(items) < max(1, limit):
        items.append(normalized)


def _whiteboard_snapshot_entries(project_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(project_context, dict):
        return []
    whiteboard = project_context.get("whiteboard", {})
    if not isinstance(whiteboard, dict):
        return []
    snapshot = whiteboard.get("snapshot", {})
    if not isinstance(snapshot, dict):
        return []
    entries = snapshot.get("entries", [])
    return [item for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []


def _progress_inputs(project_context: dict[str, Any], task_summary_hint: str) -> dict[str, Any]:
    runtime_state = _project_runtime_state(project_context)
    runtime_latest = runtime_state.get("latest_result", {})
    if not isinstance(runtime_latest, dict):
        runtime_latest = {}
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = runtime_state.get("gate", {})
    if not isinstance(gate, dict) or not gate:
        gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    return {
        "runtime_state": runtime_state,
        "runtime_latest": runtime_latest,
        "status": status,
        "gate": gate,
        "decisions": project_context.get("decisions", {}) if isinstance(project_context.get("decisions", {}), dict) else {},
        "run_id": sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80),
        "task_goal": sanitize_inline_text(str(task_summary_hint or project_context.get("goal", "")).strip(), max_chars=260),
    }


def _recovery_snapshot(project_context: dict[str, Any], gate: dict[str, Any], runtime_state: dict[str, Any]) -> dict[str, Any]:
    recovery = runtime_state.get("recovery", {})
    if not isinstance(recovery, dict):
        recovery = {}
    support_recovery = project_context.get("support_recovery", {})
    if not isinstance(support_recovery, dict):
        support_recovery = {}
    return {
        "expected_artifact": sanitize_inline_text(str(gate.get("expected_artifact", "") or recovery.get("expected_artifact", "") or support_recovery.get("expected_artifact", "")), max_chars=180),
        "recovery_action": sanitize_inline_text(str(gate.get("recovery_action", "") or recovery.get("recovery_action", "") or support_recovery.get("recovery_action", "")), max_chars=220),
        "retry_count": int(gate.get("retry_count", recovery.get("retry_count", support_recovery.get("retry_count", 0) or 0)) or 0),
        "max_retries": int(gate.get("max_retries", recovery.get("max_retries", support_recovery.get("max_retries", 0) or 0)) or 0),
        "needed": bool(recovery.get("needed", False) or support_recovery.get("needed", False)),
        "hint": sanitize_inline_text(str(support_recovery.get("hint", "") or recovery.get("hint", "")), max_chars=220),
        "last_attempt": sanitize_inline_text(str(support_recovery.get("last_attempt", "") or recovery.get("last_attempt", "")), max_chars=160),
    }


def _done_items(project_context: dict[str, Any], run_id: str) -> list[str]:
    done_items: list[str] = []
    if run_id:
        _append_progress_item(done_items, "我这边已经接手到后台流程")
    for entry in _whiteboard_snapshot_entries(project_context):
        _append_done_item_from_whiteboard(done_items, entry)
    return done_items


def _append_done_item_from_whiteboard(done_items: list[str], entry: dict[str, Any]) -> None:
    kind = str(entry.get("kind", "")).strip().lower()
    text = str(entry.get("text", "")).strip()
    if kind in {"dispatch_lookup", "support_lookup"} and "lookup completed" in text.lower():
        _append_progress_item(done_items, "资料检索已完成")
        return
    if kind != "dispatch_result":
        return
    match = _WHITEBOARD_DISPATCH_RESULT_RE.match(text)
    if not match or str(match.group("status") or "").strip().lower() != "executed":
        return
    label = _progress_step_label(
        action=str(match.group("action") or ""),
        target_path=str(match.group("target") or ""),
        role=str(match.group("role") or ""),
        reason=str(match.group("reason") or ""),
    )
    if label:
        _append_progress_item(done_items, "资料检索已完成" if label == "资料检索" else f"{label}已完成")


def _decision_snapshot(runtime_state: dict[str, Any], status: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    rows = runtime_state.get("pending_decisions", [])
    if not isinstance(rows, list) or not rows:
        rows = decisions.get("decisions", [])
    if not isinstance(rows, list):
        rows = []
    question = ""
    pending = submitted = 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        state = sanitize_inline_text(str(item.get("status", "")), max_chars=24).lower()
        hint = sanitize_inline_text(str(item.get("question", "") or item.get("question_hint", "")), max_chars=220)
        pending += 1 if state == "pending" else 0
        submitted += 1 if state == "submitted" else 0
        question = question or hint
    count = int(runtime_state.get("decisions_needed_count", pending) or pending)
    waiting = bool(runtime_state.get("needs_user_decision", False) or status.get("needs_user_decision", False) or count > 0)
    return {"question": question, "pending_count": pending, "submitted_count": submitted, "count": count, "waiting": waiting}


def _stage_base(runtime_phase: str) -> tuple[str, str]:
    stage = _runtime_phase_to_support_stage(runtime_phase) or "PLAN"
    reason = f"canonical_phase:{runtime_phase.lower()}" if runtime_phase else "default_from_status"
    return stage, reason


def _final_progress_state(verify_result: str, run_status: str) -> dict[str, str] | None:
    if verify_result == "PASS" and run_status in {"pass", "done", "completed", "success"}:
        return {"phase": "结果整理/交付", "blocker": "none", "next_action": "把这一轮结果和可交付内容整理给你", "purpose": "delivery", "stage": "FINALIZE", "reason": "verify_pass_or_final_run_status"}
    return None


def _decision_progress_state(decision: dict[str, Any]) -> dict[str, str] | None:
    if decision["waiting"]:
        return {"phase": "等待你的决定", "blocker": "等你先确认一个关键决定", "next_action": "等你拍板这个点，一收到答复我就马上继续推进", "question_needed": "yes", "stage": "WAIT_USER_DECISION", "reason": "decision_required"}
    if decision["submitted_count"] > 0:
        return {"phase": "执行推进", "blocker": "你的决策已提交，正在等待后端消费确认", "next_action": "我会继续轮询后端消费状态，一旦确认推进就马上同步你", "stage": "EXECUTE", "reason": "decision_submitted_waiting_consume"}
    return None


def _recovery_progress_state(runtime_phase: str, gate_reason: str, gate_label: str, recovery: dict[str, Any]) -> dict[str, str] | None:
    if runtime_phase not in {"RETRYING", "RECOVERY_NEEDED", "EXEC_FAILED", "BLOCKED_HARD"}:
        return None
    labels = {"RETRYING": "自动恢复重试", "RECOVERY_NEEDED": "等待明确恢复", "EXEC_FAILED": "执行失败", "BLOCKED_HARD": "硬阻塞"}
    phase = labels.get(runtime_phase, "异常恢复")
    if runtime_phase == "EXEC_FAILED":
        blocker = gate_reason or "provider 已报告执行，但目标产物仍未落地"
        action = recovery["recovery_action"] or "先核对 provider 执行证据，再重跑失败 gate"
    elif runtime_phase == "RECOVERY_NEEDED":
        blocker = gate_reason or f"{gate_label or '当前 gate'} 自动恢复已耗尽"
        action = recovery["recovery_action"] or "进入明确恢复处理，先检查 gate truth 与产物落地原因"
    elif runtime_phase == "BLOCKED_HARD":
        blocker = gate_reason or f"{gate_label or '当前 gate'} 缺少可自动恢复的目标产物"
        action = recovery["recovery_action"] or "先人工对齐 blocker truth，再决定恢复路径"
    else:
        artifact = recovery["expected_artifact"].rsplit("/", 1)[-1] if recovery["expected_artifact"] else ""
        blocker = gate_reason or (f"当前缺的是 {artifact}" if artifact else "当前 gate 已进入自动恢复重试")
        action = recovery["recovery_action"] or "继续自动重试当前 stalled gate，并确认目标产物是否落地"
    if recovery["retry_count"] > 0 and recovery["max_retries"] > 0:
        action = sanitize_inline_text(f"已自动重试 {recovery['retry_count']}/{recovery['max_retries']} 次；下一步：{action}", max_chars=220)
    return {"phase": phase, "blocker": blocker, "next_action": action, "stage": runtime_phase, "reason": f"watchdog_{runtime_phase.lower()}"}


def _blocked_progress_state(project_context: dict[str, Any], gate_state: str, gate_reason: str, gate_label: str, recovery: dict[str, Any]) -> dict[str, str] | None:
    if gate_state != "blocked":
        return None
    if is_missing_plan_draft_context(project_context):
        return {"phase": gate_label or "方案整理", "blocker": gate_reason or "方案整理这一步还卡着，当前缺的是 PLAN_draft.md", "next_action": recovery["hint"] or plan_draft_recovery_hint(attempted=bool(recovery["last_attempt"])), "stage": "RECOVER", "reason": "blocked_state_detected"}
    blocker = f"{gate_label}这一步还卡着，后续推进要先等这个点处理掉" if gate_label else gate_reason or "当前评审这一步还卡着，后续推进要先等这个点处理掉"
    action = recovery["recovery_action"] or (f"先把{gate_label}卡点处理掉，再重新对齐最新 gate truth" if gate_label else "先把当前卡点处理掉，再重新对齐最新 gate truth")
    if recovery["needed"] and recovery["hint"]:
        action = recovery["hint"] if not recovery["last_attempt"] else sanitize_inline_text(f"{recovery['last_attempt']}；下一步：{recovery['hint']}", max_chars=220)
    return {"phase": gate_label or "当前评审", "blocker": blocker, "next_action": action, "stage": "RECOVER", "reason": "blocked_state_detected"}


def _progress_state(project_context: dict[str, Any], snap: dict[str, Any], decision: dict[str, Any], recovery: dict[str, Any]) -> dict[str, str]:
    runtime_state, status, gate = snap["runtime_state"], snap["status"], snap["gate"]
    run_status = str(runtime_state.get("run_status", "")).strip().lower() or str(status.get("run_status", "")).strip().lower()
    verify_result = str(runtime_state.get("verify_result", "")).strip().upper() or str(snap["runtime_latest"].get("verify_result", "")).strip().upper() or str(status.get("verify_result", "")).strip().upper()
    runtime_phase = sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40).upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    gate_reason = sanitize_inline_text(str(runtime_state.get("blocking_reason", "")).strip() or str(gate.get("reason", "")).strip(), max_chars=220)
    gate_label = _progress_step_label(target_path=str(gate.get("path", "")), role=str(gate.get("owner", "")), reason=gate_reason)
    stage, reason = _stage_base(runtime_phase)
    base = {"phase": _phase_label(stage) or gate_label or "处理中", "blocker": "none", "next_action": "继续对齐最新 gate truth，并在阶段变化时马上同步你", "purpose": "progress", "question_needed": "no", "stage": stage, "reason": reason}
    for candidate in (_final_progress_state(verify_result, run_status), _decision_progress_state(decision), _recovery_progress_state(runtime_phase, gate_reason, gate_label, recovery), _blocked_progress_state(project_context, gate_state, gate_reason, gate_label, recovery)):
        if candidate:
            base.update(candidate)
            break
    if not any(base.get("reason") == marker for marker in {"verify_pass_or_final_run_status", "decision_required", "decision_submitted_waiting_consume", "blocked_state_detected"}) and run_status in {"running", "in_progress", "working"}:
        base.update({"phase": _phase_label(stage) or gate_label or "执行推进", "stage": "EXECUTE", "reason": "run_status_running"})
    if base["blocker"] == "none" and gate_reason and gate_reason.lower() not in {"none", "n/a"} and base["stage"] in {"RECOVER", "VERIFY"}:
        base["blocker"] = gate_reason
    return base


def _phase_label(stage: str) -> str:
    return {
        "INTAKE": "需求确认",
        "CLARIFY": "需求澄清",
        "PLAN": "方案规划",
        "EXECUTE": "执行推进",
        "VERIFY": "验证收敛",
        "FINALIZE": "结果整理/交付",
        "DELIVER": "结果整理/交付",
        "DELIVERED": "结果已回传",
        "RECOVER": "异常恢复",
    }.get(stage, "")


def _proof_refs(project_context: dict[str, Any], run_id: str, runtime_latest: dict[str, Any]) -> list[str]:
    refs = [f"run_id={run_id}"] if run_id else []
    runtime_refs = runtime_latest.get("proof_refs", [])
    if isinstance(runtime_refs, list):
        for item in runtime_refs:
            ref = sanitize_inline_text(str(item), max_chars=180)
            if ref and ref not in refs:
                refs.append(ref)
                if len(refs) >= 4:
                    break
    return refs


def build_progress_binding(*, project_context: dict[str, Any] | None, task_summary_hint: str = "") -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    snap = _progress_inputs(project_context, task_summary_hint)
    recovery = _recovery_snapshot(project_context, snap["gate"], snap["runtime_state"])
    decision = _decision_snapshot(snap["runtime_state"], snap["status"], snap["decisions"])
    state = _progress_state(project_context, snap, decision, recovery)
    return {
        "current_task_goal": snap["task_goal"],
        "current_phase": state["phase"],
        "active_stage": state["stage"],
        "stage_reason": state["reason"],
        "stage_exit_condition": SUPPORT_STAGE_EXIT_RULES.get(state["stage"], ""),
        "last_confirmed_items": _done_items(project_context, snap["run_id"]),
        "current_blocker": state["blocker"],
        "message_purpose": state.get("purpose", "progress"),
        "question_needed": state.get("question_needed", "no"),
        "next_action": sanitize_inline_text(state["next_action"], max_chars=220),
        "blocking_question": decision["question"],
        "proof_refs": _proof_refs(project_context, snap["run_id"], snap["runtime_latest"]),
    }


def build_progress_digest(*, project_context: dict[str, Any] | None, task_summary_hint: str = "") -> tuple[str, dict[str, Any]]:
    if not isinstance(project_context, dict):
        return "", {}
    binding = build_progress_binding(project_context=project_context, task_summary_hint=task_summary_hint)
    if not binding:
        return "", {}
    snap = _progress_inputs(project_context, task_summary_hint)
    payload = {
        "run_id": snap["run_id"],
        "phase": sanitize_inline_text(str(snap["runtime_state"].get("phase", "")), max_chars=40),
        "run_status": sanitize_inline_text(str(snap["runtime_state"].get("run_status", "")).strip() or str(snap["status"].get("run_status", "")).strip(), max_chars=40),
        "verify_result": sanitize_inline_text(str(snap["runtime_state"].get("verify_result", "")).strip() or str(snap["status"].get("verify_result", "")).strip(), max_chars=20),
        "gate_state": sanitize_inline_text(str(snap["gate"].get("state", "")), max_chars=40),
        "gate_reason": sanitize_inline_text(str(snap["runtime_state"].get("blocking_reason", "")).strip() or str(snap["gate"].get("reason", "")).strip(), max_chars=220),
        "needs_user_decision": bool(snap["runtime_state"].get("needs_user_decision", False) or snap["status"].get("needs_user_decision", False)),
        "progress_binding": binding,
    }
    raw = json.dumps(clean_json_value(payload), ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest(), binding


def remember_progress_notification(session_state: dict[str, Any], *, project_context: dict[str, Any] | None, task_summary_hint: str = "", ts: str = "", status_hash: str = "") -> None:
    if not isinstance(project_context, dict):
        return
    run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
    if not run_id:
        return
    digest, binding = build_progress_digest(project_context=project_context, task_summary_hint=task_summary_hint)
    stable_hash = sanitize_inline_text(status_hash, max_chars=80) or digest
    if not stable_hash:
        return
    notification_state = latest_notification_state(session_state)
    notification_state["last_progress_hash"] = stable_hash
    notification_state["last_progress_ts"] = sanitize_inline_text(ts or now_iso(), max_chars=40)
    notification_state["last_notified_run_id"] = run_id
    notification_state["last_notified_phase"] = sanitize_inline_text(str(binding.get("current_phase", "")), max_chars=80)


def should_auto_advance_project_context(session_state: dict[str, Any], project_context: dict[str, Any] | None) -> bool:
    return should_auto_advance_project_context_impl(
        project_context,
        last_auto_advance_ts=str(latest_notification_state(session_state).get("last_auto_advance_ts", "")),
        interval_sec=SUPPORT_AUTO_ADVANCE_INTERVAL_SEC,
        seconds_since=seconds_since,
    )


__all__ = [
    "_progress_step_label",
    "_append_progress_item",
    "_whiteboard_snapshot_entries",
    "build_progress_binding",
    "build_progress_digest",
    "remember_progress_notification",
    "should_auto_advance_project_context",
]
