from __future__ import annotations

from typing import Any, Mapping

from .progress_reply import humanize_progress_runtime_text


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _dedupe_items(items: list[str], *, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = _norm(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(1, limit):
            break
    return out


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _project_row(project_context: Mapping[str, Any] | None, *keys: str) -> Mapping[str, Any]:
    source = _as_mapping(project_context)
    for key in keys:
        row = _as_mapping(source.get(key, {}))
        if row:
            return row
    return {}


def _decision_prompt(project_context: Mapping[str, Any] | None) -> str:
    render = _project_row(project_context, "render_snapshot", "render_state_snapshot", "render_state")
    cards = render.get("decision_cards", [])
    if isinstance(cards, list):
        for item in cards:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if question:
                return question
    runtime = _project_row(project_context, "runtime_state")
    pending = runtime.get("pending_decisions", [])
    if isinstance(pending, list):
        for item in pending:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", "") or row.get("reason", ""))
            if question:
                return question
    return ""


def _progress_binding_fields(source: Mapping[str, Any] | None) -> tuple[str, list[str]]:
    row = _as_mapping(source)
    binding = _as_mapping(row.get("progress_binding", {}))
    phase = _norm(
        row.get("current_phase", "")
        or row.get("reply_truth_current_phase", "")
        or binding.get("current_phase", "")
    )
    done_items_raw: Any = row.get("last_confirmed_items")
    if not isinstance(done_items_raw, list) or not done_items_raw:
        done_items_raw = row.get("reply_truth_last_confirmed_items")
    if not isinstance(done_items_raw, list) or not done_items_raw:
        done_items_raw = binding.get("last_confirmed_items")
    if not isinstance(done_items_raw, list):
        done_items_raw = []
    done_items = _dedupe_items([str(item or "") for item in done_items_raw], limit=3)
    return phase, done_items


def context_internal_recovery_details(project_context: Mapping[str, Any] | None) -> dict[str, str | bool | int]:
    render = _project_row(project_context, "render_snapshot", "render_state_snapshot", "render_state")
    current = _project_row(project_context, "current_snapshot", "current_state_snapshot", "current_state")
    runtime = _project_row(project_context, "runtime_state")
    status = _project_row(project_context, "status")
    gate = _as_mapping(status.get("gate", {}))
    recovery = _project_row(project_context, "support_recovery")
    runtime_recovery = _as_mapping(runtime.get("recovery", {}))
    if runtime_recovery:
        recovery = runtime_recovery
    waiting_for_decision = bool(runtime.get("needs_user_decision", False)) or bool(status.get("needs_user_decision", False))
    blocker = _norm(current.get("current_blocker", "") or runtime.get("blocking_reason", "") or gate.get("reason", "") or render.get("progress_summary", ""))
    next_action = _norm(current.get("next_action", "") or runtime.get("next_action", "") or recovery.get("hint", "") or recovery.get("last_attempt", ""))
    retry_count = int(recovery.get("retry_count", gate.get("retry_count", 0) or 0) or 0)
    max_retries = int(recovery.get("max_retries", gate.get("max_retries", 0) or 0) or 0)
    recovery_action = _norm(recovery.get("recovery_action", "") or gate.get("recovery_action", ""))
    recovery_status = _norm(recovery.get("status", "") or gate.get("watchdog_status", "")).lower()
    has_internal_recovery = bool(blocker) and not waiting_for_decision and (not _decision_prompt(project_context)) and (
        _norm(current.get("authoritative_stage", "") or runtime.get("phase", "")).upper() in {"RECOVER", "RETRYING", "RECOVERY_NEEDED", "EXEC_FAILED", "BLOCKED_HARD"}
        or _norm(render.get("visible_state", "")).upper() == "BLOCKED_NEEDS_INPUT"
        or bool(recovery.get("needed", False))
        or recovery_status in {"retry_ready", "retrying", "required", "recovery_needed", "exec_failed", "blocked_hard"}
    )
    return {
        "has_internal_recovery": has_internal_recovery,
        "blocker": blocker,
        "next_action": next_action,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "recovery_action": recovery_action,
        "recovery_status": recovery_status,
    }


def backend_truth_details(source: Mapping[str, Any] | None) -> dict[str, Any]:
    row = _as_mapping(source)
    phase, done_items = _progress_binding_fields(row)
    status = _norm(
        row.get("reply_truth_status", "")
        or row.get("status", "")
    ).lower()
    reason = _norm(row.get("reply_truth_reason", "") or row.get("reason", "") or row.get("blocker", ""))
    next_action = _norm(row.get("reply_truth_next_action", "") or row.get("next_action", ""))
    source_confidence = _norm(row.get("reply_source_confidence", "")).lower()
    if not status:
        return {
            "has_truth": False,
            "status": "",
            "reason": "",
            "next_action": "",
            "source_confidence": "",
            "current_phase": "",
            "last_confirmed_items": [],
        }
    return {
        "has_truth": True,
        "status": status,
        "reason": reason,
        "next_action": next_action,
        "source_confidence": source_confidence,
        "current_phase": phase,
        "last_confirmed_items": done_items,
    }


def context_reply_truth_details(project_context: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _as_mapping(project_context)
    reply_truth = _project_row(source, "support_reply_truth")
    return backend_truth_details(reply_truth)


def render_backend_truth_text(
    *,
    lang_hint: str,
    status: str = "",
    reason: str = "",
    next_action: str = "",
    source_confidence: str = "",
    current_phase: str = "",
    last_confirmed_items: list[str] | tuple[str, ...] | None = None,
) -> str:
    lang = _norm(lang_hint).lower()
    truth = _norm(status).lower()
    clean_reason = humanize_progress_runtime_text(reason, lang=lang)
    clean_next_action = humanize_progress_runtime_text(next_action, lang=lang)
    low_confidence = _norm(source_confidence).lower() == "low"
    clean_phase = _norm(current_phase)
    done_items = _dedupe_items([str(item or "") for item in list(last_confirmed_items or [])], limit=3)
    if lang.startswith("en"):
        if truth == "backend_unavailable":
            head = "The backend reply path is unavailable right now, so there is no customer-ready reply for this turn yet."
        elif truth == "backend_deferred":
            head = "This turn has reached the backend, but there is still no customer-ready reply yet."
        elif truth == "backend_failed":
            head = f"This backend attempt failed: {clean_reason}." if clean_reason else "This backend attempt failed before producing a customer-ready reply."
        elif truth == "backend_blocked":
            head = f"The backend is currently blocked on: {clean_reason}." if clean_reason else "The backend is currently blocked."
        elif truth == "low_confidence_fallback":
            head = "The formal reply path did not yield a customer-ready answer; only a low-confidence fallback summary is available right now."
        else:
            head = "There is no customer-ready backend reply for this turn yet."
        rows = [head]
        if clean_phase:
            rows.append(f"Current phase: {clean_phase}.")
        if done_items:
            rows.append(f"Confirmed progress so far: {'; '.join(done_items)}.")
        if clean_next_action:
            rows.append(f"Next I will handle: {clean_next_action}.")
        elif low_confidence:
            rows.append("I will wait for a stronger backend result before claiming new progress.")
        return " ".join(rows).strip()

    if truth == "backend_unavailable":
        head = "当前后端回复链暂时不可用，所以这轮还没有可直接发送的正式回复。"
    elif truth == "backend_deferred":
        head = "这轮请求已经进了后端，但目前还没有可直接发送的正式回复。"
    elif truth == "backend_failed":
        head = f"这轮后端执行失败了：{clean_reason}。" if clean_reason else "这轮后端执行失败了，暂时还没有可直接发送的正式回复。"
    elif truth == "backend_blocked":
        head = f"当前后端卡在：{clean_reason}。" if clean_reason else "当前后端处于阻塞状态。"
    elif truth == "low_confidence_fallback":
        head = "当前正式回复链没有给出可直接发送的结果，眼下只有一份低置信度兜底说明。"
    else:
        head = "这轮后端暂时还没有可直接发送的正式回复。"
    rows = [head]
    if clean_phase:
        rows.append(f"当前阶段：{clean_phase}。")
    if done_items:
        rows.append("已确认进展：" + "、".join(done_items) + "。")
    if clean_next_action:
        rows.append(f"下一步我会先处理：{clean_next_action}。")
    elif low_confidence:
        rows.append("我会等后端给出更扎实的结果后，再同步新的进展。")
    return "\n\n".join(rows).strip()


def render_internal_recovery_text(
    *,
    lang_hint: str,
    blocker: str = "",
    next_action: str = "",
    retry_count: int = 0,
    max_retries: int = 0,
    recovery_action: str = "",
) -> str:
    lang = _norm(lang_hint).lower()
    clean_blocker = _norm(blocker)
    clean_next_action = _norm(next_action)
    clean_recovery_action = _norm(recovery_action)
    if clean_blocker.lower().startswith("waiting for "):
        missing_target = clean_blocker[12:].strip()
        clean_blocker = f"the missing item is {missing_target}" if lang.startswith("en") else f"当前缺的是 {missing_target}"
    if lang.startswith("en"):
        rows = [f"There is an internal blocker right now: {clean_blocker}." if clean_blocker else "There is an internal blocker right now, but no extra input is needed from you."]
        if retry_count > 0 and max_retries > 0:
            rows.append(f"The system has already auto-retried {retry_count}/{max_retries} times.")
        if clean_next_action:
            rows.append(f"Next I will handle: {clean_next_action}.")
        elif clean_recovery_action:
            rows.append(f"Recovery action: {clean_recovery_action}.")
        rows.append("I will send the next visible update as soon as this recovery step moves forward.")
        return " ".join(rows)
    rows = [f"当前遇到内部阻塞：{clean_blocker}。" if clean_blocker else "当前遇到内部阻塞，但这一步不需要你额外补信息。"]
    if retry_count > 0 and max_retries > 0:
        rows.append(f"系统已自动重试 {retry_count}/{max_retries} 次。")
    if clean_next_action:
        rows.append(f"我会先处理：{clean_next_action}。")
    elif clean_recovery_action:
        rows.append(f"下一步恢复动作：{clean_recovery_action}。")
    rows.append("这边一有新的可见变化就马上同步你。")
    return "\n\n".join(rows)


def apply_frontdesk_truth_state(
    raw_backend_state: Mapping[str, Any] | None,
    *,
    frontdesk_state: Mapping[str, Any] | None,
    raw_next_question: str,
) -> tuple[dict[str, Any], str]:
    raw_backend = dict(raw_backend_state or {})
    frontdesk = _as_mapping(frontdesk_state)
    frontdesk_name = _norm(frontdesk.get("state", "")).lower()
    if frontdesk_name not in {"showing_error", "error"}:
        return raw_backend, raw_next_question
    blocker = _norm(frontdesk.get("blocked_reason", ""))
    next_action = _norm(frontdesk.get("next_action", ""))
    needs_user_input = bool(_norm(raw_next_question))
    raw_backend["blocked_needs_input"] = needs_user_input
    raw_backend["needs_input"] = needs_user_input
    if blocker and not _norm(raw_backend.get("reason", "")):
        raw_backend["reason"] = blocker
    if not needs_user_input:
        raw_backend["reply_truth_status"] = _norm(raw_backend.get("reply_truth_status", "")) or "backend_blocked"
        raw_backend["reply_truth_reason"] = _norm(raw_backend.get("reply_truth_reason", "")) or blocker
        raw_backend["reply_truth_next_action"] = _norm(raw_backend.get("reply_truth_next_action", "")) or next_action
    return raw_backend, raw_next_question


def reply_truth_note_fields(
    source: Mapping[str, Any] | None,
    *,
    internal_blocker: str = "",
    next_action: str = "",
    temporary_failure: bool = False,
    allow_internal_error_rewrite: bool = True,
) -> dict[str, Any]:
    reply_truth = backend_truth_details(source)
    return {
        "internal_blocker": internal_blocker,
        "recovery_next_action": _norm(next_action) or str(reply_truth.get("next_action", "")),
        "reply_truth_status": str(reply_truth.get("status", "")),
        "reply_truth_reason": str(reply_truth.get("reason", "")),
        "reply_truth_next_action": str(reply_truth.get("next_action", "")) or _norm(next_action),
        "reply_source_confidence": str(reply_truth.get("source_confidence", "")),
        "reply_truth_current_phase": str(reply_truth.get("current_phase", "")),
        "reply_truth_last_confirmed_items": list(reply_truth.get("last_confirmed_items", []))
        if isinstance(reply_truth.get("last_confirmed_items", []), list)
        else [],
        "backend_temporary_failure": bool(temporary_failure),
        "allow_internal_error_rewrite": bool(allow_internal_error_rewrite),
    }


def context_truth_reply(project_context: Mapping[str, Any] | None, *, lang_hint: str) -> str:
    reply_truth = context_reply_truth_details(project_context)
    if not bool(reply_truth.get("has_truth", False)):
        return ""
    return render_backend_truth_text(
        lang_hint=lang_hint,
        status=str(reply_truth.get("status", "")),
        reason=str(reply_truth.get("reason", "")),
        next_action=str(reply_truth.get("next_action", "")),
        source_confidence=str(reply_truth.get("source_confidence", "")),
        current_phase=str(reply_truth.get("current_phase", "")),
        last_confirmed_items=reply_truth.get("last_confirmed_items", []),
    )
