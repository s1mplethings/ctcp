#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

CONTROLLER_STATES: tuple[str, ...] = (
    "BOOTSTRAP",
    "SYNC_CONTEXT",
    "AUTO_ADVANCE_READY",
    "WAIT_USER_DECISION",
    "WAIT_EXECUTION",
    "NOTIFY_PROGRESS",
    "NOTIFY_RESULT",
    "ERROR_RECOVERY",
)

_FINAL_RUN_STATUSES = {"pass", "done", "completed", "success"}
_ERROR_RUN_STATUSES = {"fail", "failed", "error", "aborted"}
_ERROR_GATE_STATES = {"error", "failed"}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso_ts(text: str) -> dt.datetime | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _seconds_since(text: str, *, now_ts: str) -> float | None:
    base = _parse_iso_ts(text)
    now = _parse_iso_ts(now_ts)
    if base is None or now is None:
        return None
    return max(0.0, (now - base).total_seconds())


def _state_zone(session_state: dict[str, Any], key: str) -> dict[str, Any]:
    value = session_state.get(key)
    if not isinstance(value, dict):
        value = {}
        session_state[key] = value
    return value


def _list_zone(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        value = []
        parent[key] = value
    return value


def _notification_state(session_state: dict[str, Any]) -> dict[str, Any]:
    zone = _state_zone(session_state, "notification_state")
    zone.setdefault("last_progress_hash", "")
    zone.setdefault("last_progress_ts", "")
    zone.setdefault("last_notified_run_id", "")
    zone.setdefault("last_notified_phase", "")
    zone.setdefault("last_auto_advance_ts", "")
    zone.setdefault("last_seen_status_hash", "")
    zone.setdefault("last_sent_message_hash", "")
    zone.setdefault("last_sent_kind", "")
    zone.setdefault("last_decision_prompt_hash", "")
    zone.setdefault("cooldown_until_ts", "")
    return zone


def _controller_state(session_state: dict[str, Any]) -> dict[str, Any]:
    zone = _state_zone(session_state, "controller_state")
    zone.setdefault("current", "BOOTSTRAP")
    zone.setdefault("last_transition_ts", "")
    zone.setdefault("last_reason", "")
    return zone


def _outbound_queue(session_state: dict[str, Any]) -> dict[str, Any]:
    zone = _state_zone(session_state, "outbound_queue")
    _list_zone(zone, "pending_ids")
    _list_zone(zone, "jobs")
    return zone


def _status_view(project_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    render_snapshot = project_context.get("render_snapshot", {}) or project_context.get("render_state_snapshot", {})
    if not isinstance(render_snapshot, dict):
        render_snapshot = {}
    current_snapshot = project_context.get("current_snapshot", {}) or project_context.get("current_state_snapshot", {})
    if not isinstance(current_snapshot, dict):
        current_snapshot = {}
    runtime_state = project_context.get("runtime_state", {})
    if not isinstance(runtime_state, dict):
        runtime_state = {}
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = runtime_state.get("gate", {})
    if (not isinstance(gate, dict)) or (not gate):
        gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    latest_result = runtime_state.get("latest_result", {})
    if not isinstance(latest_result, dict):
        latest_result = {}
    runtime_error = runtime_state.get("error", {})
    if not isinstance(runtime_error, dict):
        runtime_error = {}
    render_cards = render_snapshot.get("decision_cards", [])
    if not isinstance(render_cards, list):
        render_cards = []
    pending_rows = [row for row in render_cards if isinstance(row, dict)]
    if not pending_rows:
        runtime_pending = runtime_state.get("pending_decisions", [])
        if isinstance(runtime_pending, list):
            pending_rows = [row for row in runtime_pending if isinstance(row, dict)]
    runtime_decisions_explicit = isinstance(runtime_state, dict) and ("pending_decisions" in runtime_state)
    if (not pending_rows) and (not runtime_decisions_explicit):
        decisions = project_context.get("decisions", {})
        if isinstance(decisions, dict):
            decision_rows = decisions.get("decisions", [])
            if isinstance(decision_rows, list):
                pending_rows = [row for row in decision_rows if isinstance(row, dict)]
    pending_count = sum(
        1 for row in pending_rows if str(row.get("status", "")).strip().lower() in {"", "pending"}
    )
    open_count = len(pending_rows)
    visible_state = str(render_snapshot.get("visible_state", "")).strip().upper()
    ui_badge = str(render_snapshot.get("ui_badge", "")).strip().lower()
    needs_user_decision = bool(pending_count > 0 or visible_state == "WAITING_FOR_DECISION")
    verify_result = str(runtime_state.get("verify_result", "")).strip().upper()
    if not verify_result:
        verify_result = str(latest_result.get("verify_result", "")).strip().upper()
    if not verify_result:
        verify_result = str(status.get("verify_result", "")).strip().upper()
    run_status = str(runtime_state.get("run_status", "")).strip().lower()
    if not run_status:
        run_status = str(status.get("run_status", "")).strip().lower()
    gate_state = str(gate.get("state", "")).strip().lower()
    result_event = project_context.get("result_event", {})
    if not isinstance(result_event, dict):
        result_event = {}
    artifact_manifest = project_context.get("artifact_manifest", {})
    if not isinstance(artifact_manifest, dict):
        artifact_manifest = {}
    output_artifacts = project_context.get("output_artifacts", {})
    if not isinstance(output_artifacts, dict):
        output_artifacts = {}
    output_rows = output_artifacts.get("artifacts", [])
    output_count = len(output_rows) if isinstance(output_rows, list) else 0
    final_signaled = bool(
        visible_state == "DONE"
        and (result_event or artifact_manifest or output_count > 0)
    )
    authoritative_stage = str(current_snapshot.get("authoritative_stage", "")).strip().upper() or str(runtime_state.get("phase", "")).strip().upper()
    has_error = bool(runtime_error.get("has_error", False)) or authoritative_stage in {"FAILED"} or ui_badge in {"error"} or visible_state in {"ERROR"}
    if not has_error:
        has_error = run_status in _ERROR_RUN_STATUSES or gate_state in _ERROR_GATE_STATES
    return {
        "run_id": str(project_context.get("run_id", "")).strip(),
        "phase": authoritative_stage,
        "visible_state": visible_state,
        "ui_badge": ui_badge,
        "progress_summary": str(render_snapshot.get("progress_summary", "")).strip(),
        "run_status": run_status,
        "verify_result": verify_result,
        "gate_state": str(gate.get("state", "")).strip().lower(),
        "gate_reason": str(gate.get("reason", "")).strip(),
        "gate_owner": str(gate.get("owner", "")).strip(),
        "blocking_reason": str(runtime_state.get("blocking_reason", "")).strip(),
        "decisions_needed_count": int(pending_count),
        "open_decisions_count": int(runtime_state.get("open_decisions_count", open_count) or open_count),
        "needs_user_decision": bool(needs_user_decision),
        "has_error": bool(has_error),
        "final_signaled": bool(final_signaled),
        "pending_decisions": pending_rows,
    }


def _decision_prompt(project_context: dict[str, Any] | None) -> tuple[str, str]:
    if not isinstance(project_context, dict):
        return "", ""
    render_snapshot = project_context.get("render_snapshot", {}) or project_context.get("render_state_snapshot", {})
    if isinstance(render_snapshot, dict):
        cards = render_snapshot.get("decision_cards", [])
        if isinstance(cards, list):
            for item in cards:
                if not isinstance(item, dict):
                    continue
                question = str(item.get("question", "") or item.get("question_hint", "")).strip()
                if question:
                    digest = hashlib.sha1(question.encode("utf-8", errors="replace")).hexdigest()
                    return question, digest
    runtime_state = project_context.get("runtime_state", {})
    if isinstance(runtime_state, dict):
        rows = runtime_state.get("pending_decisions", [])
        if isinstance(rows, list):
            for item in rows:
                if not isinstance(item, dict):
                    continue
                status = str(item.get("status", "")).strip().lower()
                if status and status != "pending":
                    continue
                question = str(item.get("question", "") or item.get("question_hint", "")).strip()
                if question:
                    digest = hashlib.sha1(question.encode("utf-8", errors="replace")).hexdigest()
                    return question, digest
    decisions = project_context.get("decisions", {})
    if not isinstance(decisions, dict):
        decisions = {}
    rows = decisions.get("decisions", [])
    if not isinstance(rows, list):
        rows = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question_hint", "") or item.get("question", "")).strip()
        if question:
            digest = hashlib.sha1(question.encode("utf-8", errors="replace")).hexdigest()
            return question, digest
    return "", ""


def _status_hash(view: dict[str, Any], *, progress_binding: dict[str, Any] | None = None) -> str:
    payload = {
        "run_id": str(view.get("run_id", "")).strip(),
        "phase": str(view.get("phase", "")).strip(),
        "run_status": str(view.get("run_status", "")).strip(),
        "verify_result": str(view.get("verify_result", "")).strip(),
        "gate_state": str(view.get("gate_state", "")).strip(),
        "gate_reason": str(view.get("gate_reason", "")).strip(),
        "gate_owner": str(view.get("gate_owner", "")).strip(),
        "blocking_reason": str(view.get("blocking_reason", "")).strip(),
        "decisions_needed_count": int(view.get("decisions_needed_count", 0) or 0),
        "open_decisions_count": int(view.get("open_decisions_count", 0) or 0),
    }
    if isinstance(progress_binding, dict):
        payload["progress_binding"] = progress_binding
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _message_hash(kind: str, status_hash: str, *, salt: str = "") -> str:
    raw = f"{kind}:{status_hash}:{salt}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cooldown_active(notification_state: dict[str, Any], *, now_ts: str) -> bool:
    until = str(notification_state.get("cooldown_until_ts", "")).strip()
    if not until:
        return False
    now = _parse_iso_ts(now_ts)
    target = _parse_iso_ts(until)
    if now is None or target is None:
        return False
    return now < target


def _set_controller_state(controller_state: dict[str, Any], *, current: str, reason: str, now_ts: str) -> None:
    if current not in CONTROLLER_STATES:
        current = "SYNC_CONTEXT"
    previous = str(controller_state.get("current", "")).strip()
    if previous != current:
        controller_state["last_transition_ts"] = now_ts
    controller_state["current"] = current
    controller_state["last_reason"] = str(reason or "").strip()[:220]


def _enqueue_job(
    session_state: dict[str, Any],
    *,
    kind: str,
    run_id: str,
    status_hash: str,
    reason: str,
    now_ts: str,
    message_hash: str,
    decision_prompt: str = "",
    decision_prompt_hash: str = "",
) -> dict[str, Any] | None:
    queue = _outbound_queue(session_state)
    pending_ids = _list_zone(queue, "pending_ids")
    jobs = _list_zone(queue, "jobs")
    job_id = f"{kind}:{run_id or 'run'}:{message_hash[:16]}"
    if job_id in {str(item).strip() for item in pending_ids}:
        return None
    row = {
        "id": job_id,
        "kind": str(kind).strip().lower(),
        "run_id": str(run_id).strip(),
        "status_hash": str(status_hash).strip(),
        "reason": str(reason).strip(),
        "message_hash": str(message_hash).strip(),
        "decision_prompt": str(decision_prompt).strip(),
        "decision_prompt_hash": str(decision_prompt_hash).strip(),
        "created_ts": now_ts,
    }
    jobs.append(row)
    queue["jobs"] = jobs[-32:]
    pending_ids.append(job_id)
    queue["pending_ids"] = pending_ids[-64:]
    return row


def decide_and_queue(
    session_state: dict[str, Any],
    *,
    project_context: dict[str, Any] | None,
    progress_binding: dict[str, Any] | None = None,
    now_ts: str = "",
    keepalive_interval_sec: int = 900,
) -> dict[str, Any]:
    ts = str(now_ts or "").strip() or _now_iso()
    notification_state = _notification_state(session_state)
    controller_state = _controller_state(session_state)
    view = _status_view(project_context)
    run_id = str(view.get("run_id", "")).strip()

    if not run_id:
        _set_controller_state(controller_state, current="BOOTSTRAP", reason="missing_bound_run", now_ts=ts)
        return {"controller_state": "BOOTSTRAP", "reason": "missing_bound_run", "jobs": [], "status_hash": ""}

    status_hash = _status_hash(view, progress_binding=progress_binding)
    notification_state["last_seen_status_hash"] = status_hash
    visible_state = str(view.get("visible_state", "")).strip().upper()
    phase = str(view.get("phase", "")).strip().upper()
    needs_decision = bool(view.get("needs_user_decision", False)) or int(view.get("decisions_needed_count", 0) or 0) > 0
    final_ready = bool(view.get("final_signaled", False)) and (not needs_decision)
    is_error = bool(view.get("has_error", False))
    can_auto_advance = (
        (not final_ready)
        and (not needs_decision)
        and (not is_error)
        and (
            visible_state in {"EXECUTING", "UNDERSTOOD"}
            or phase in {"EXECUTE", "VERIFY", "PLAN", "INTAKE", "CLARIFY"}
        )
    )

    base_state = "WAIT_EXECUTION"
    base_reason = "waiting_execution"
    if is_error:
        base_state = "ERROR_RECOVERY"
        base_reason = "runtime_error"
    elif final_ready:
        base_state = "NOTIFY_RESULT"
        base_reason = "final_ready"
    elif needs_decision:
        base_state = "WAIT_USER_DECISION"
        base_reason = "decision_required"
    elif can_auto_advance:
        base_state = "AUTO_ADVANCE_READY"
        base_reason = "auto_advance_ready"
    else:
        base_state = "WAIT_EXECUTION"
        base_reason = "waiting_execution"
    _set_controller_state(controller_state, current=base_state, reason=base_reason, now_ts=ts)

    jobs: list[dict[str, Any]] = []
    if _cooldown_active(notification_state, now_ts=ts):
        return {"controller_state": base_state, "reason": "cooldown_active", "jobs": [], "status_hash": status_hash}

    if base_state == "WAIT_USER_DECISION":
        prompt, prompt_hash = _decision_prompt(project_context)
        if prompt_hash and prompt_hash != str(notification_state.get("last_decision_prompt_hash", "")).strip():
            message_hash = _message_hash("decision", status_hash, salt=prompt_hash)
            if message_hash != str(notification_state.get("last_sent_message_hash", "")).strip():
                job = _enqueue_job(
                    session_state,
                    kind="decision",
                    run_id=run_id,
                    status_hash=status_hash,
                    reason="decision_required",
                    now_ts=ts,
                    message_hash=message_hash,
                    decision_prompt=prompt,
                    decision_prompt_hash=prompt_hash,
                )
                if isinstance(job, dict):
                    jobs.append(job)
        return {"controller_state": "WAIT_USER_DECISION", "reason": "decision_required", "jobs": jobs, "status_hash": status_hash}

    if base_state == "NOTIFY_RESULT":
        message_hash = _message_hash("result", status_hash)
        sent_kind = str(notification_state.get("last_sent_kind", "")).strip().lower()
        if message_hash != str(notification_state.get("last_sent_message_hash", "")).strip() or sent_kind != "result":
            job = _enqueue_job(
                session_state,
                kind="result",
                run_id=run_id,
                status_hash=status_hash,
                reason="final_ready",
                now_ts=ts,
                message_hash=message_hash,
            )
            if isinstance(job, dict):
                jobs.append(job)
        return {"controller_state": "NOTIFY_RESULT", "reason": "final_ready", "jobs": jobs, "status_hash": status_hash}

    if base_state == "ERROR_RECOVERY":
        message_hash = _message_hash("error", status_hash)
        if message_hash != str(notification_state.get("last_sent_message_hash", "")).strip():
            job = _enqueue_job(
                session_state,
                kind="error",
                run_id=run_id,
                status_hash=status_hash,
                reason="runtime_error",
                now_ts=ts,
                message_hash=message_hash,
            )
            if isinstance(job, dict):
                jobs.append(job)
        return {"controller_state": "ERROR_RECOVERY", "reason": "runtime_error", "jobs": jobs, "status_hash": status_hash}

    elapsed = _seconds_since(str(notification_state.get("last_progress_ts", "")), now_ts=ts)
    interval_raw = int(keepalive_interval_sec or 0)
    if interval_raw <= 0:
        return {"controller_state": base_state, "reason": base_reason, "jobs": jobs, "status_hash": status_hash}
    keepalive_interval = float(max(120, interval_raw))
    keepalive_due = elapsed is not None and elapsed >= keepalive_interval
    if keepalive_due:
        now_dt = _parse_iso_ts(ts) or dt.datetime.now(dt.timezone.utc)
        bucket = int(now_dt.timestamp()) // max(120, interval_raw)
        salt = f"keepalive:{bucket}"
        reason = "keepalive_due"
        message_hash = _message_hash("progress", status_hash, salt=salt)
        if message_hash != str(notification_state.get("last_sent_message_hash", "")).strip():
            job = _enqueue_job(
                session_state,
                kind="progress",
                run_id=run_id,
                status_hash=status_hash,
                reason=reason,
                now_ts=ts,
                message_hash=message_hash,
            )
            if isinstance(job, dict):
                jobs.append(job)
                _set_controller_state(controller_state, current="NOTIFY_PROGRESS", reason=reason, now_ts=ts)
                return {"controller_state": "NOTIFY_PROGRESS", "reason": reason, "jobs": jobs, "status_hash": status_hash}
    return {"controller_state": base_state, "reason": base_reason, "jobs": jobs, "status_hash": status_hash}


def pop_outbound_jobs(session_state: dict[str, Any], *, max_jobs: int = 8) -> list[dict[str, Any]]:
    queue = _outbound_queue(session_state)
    jobs = _list_zone(queue, "jobs")
    limit = max(1, int(max_jobs or 1))
    out: list[dict[str, Any]] = []
    remain: list[Any] = []
    for item in jobs:
        if len(out) < limit and isinstance(item, dict):
            out.append(item)
        else:
            remain.append(item)
    queue["jobs"] = remain
    pending_ids = {str(item).strip() for item in _list_zone(queue, "pending_ids") if str(item).strip()}
    for item in out:
        pending_ids.discard(str(item.get("id", "")).strip())
    queue["pending_ids"] = [item for item in pending_ids if item][:64]
    return out


def mark_job_sent(
    session_state: dict[str, Any],
    job: dict[str, Any] | None,
    *,
    now_ts: str = "",
    cooldown_sec: int = 45,
) -> None:
    if not isinstance(job, dict):
        return
    ts = str(now_ts or "").strip() or _now_iso()
    notification_state = _notification_state(session_state)
    run_id = str(job.get("run_id", "")).strip()
    kind = str(job.get("kind", "")).strip().lower()
    status_hash = str(job.get("status_hash", "")).strip()
    message_hash = str(job.get("message_hash", "")).strip()
    if message_hash:
        notification_state["last_sent_message_hash"] = message_hash
    if kind:
        notification_state["last_sent_kind"] = kind
    if run_id:
        notification_state["last_notified_run_id"] = run_id
    if status_hash:
        notification_state["last_progress_hash"] = status_hash
    notification_state["last_progress_ts"] = ts
    if kind == "decision":
        prompt_hash = str(job.get("decision_prompt_hash", "")).strip()
        if prompt_hash:
            notification_state["last_decision_prompt_hash"] = prompt_hash
    if int(cooldown_sec or 0) <= 0:
        notification_state["cooldown_until_ts"] = ""
        return
    now = _parse_iso_ts(ts) or dt.datetime.now(dt.timezone.utc)
    until = now + dt.timedelta(seconds=max(1, int(cooldown_sec)))
    notification_state["cooldown_until_ts"] = until.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def requeue_outbound_job(session_state: dict[str, Any], job: dict[str, Any] | None, *, sanitize_inline_text: Any) -> None:
    if not isinstance(job, dict):
        return
    queue = _outbound_queue(session_state)
    jobs = _list_zone(queue, "jobs")
    pending_ids = _list_zone(queue, "pending_ids")
    job_id = sanitize_inline_text(str(job.get("id", "")), max_chars=120)
    if job_id and all(sanitize_inline_text(str(item), max_chars=120) != job_id for item in pending_ids):
        pending_ids.append(job_id)
    if not any(isinstance(item, dict) and sanitize_inline_text(str(item.get("id", "")), max_chars=120) == job_id for item in jobs):
        jobs.insert(0, dict(job))
    queue["jobs"] = jobs[:32]
    queue["pending_ids"] = pending_ids[:64]


def normalize_proactive_progress_reply_text(reply_text: str, *, lang_hint: str, leak_tokens: tuple[str, ...]) -> str:
    text = str(reply_text or "").strip()
    if not text:
        return text
    low = text.lower()
    if any(token in low for token in leak_tokens):
        if str(lang_hint or "").strip().lower().startswith("en"):
            return "Progress is moving forward as planned. I will keep pushing and sync you on the next visible update."
        return "项目在按计划推进中，我会继续往下处理，有可见进展会第一时间同步你。"
    return text


__all__ = [
    "CONTROLLER_STATES",
    "decide_and_queue",
    "mark_job_sent",
    "normalize_proactive_progress_reply_text",
    "pop_outbound_jobs",
    "requeue_outbound_job",
]
