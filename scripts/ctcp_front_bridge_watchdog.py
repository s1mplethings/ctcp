from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Callable


WATCHDOG_STALL_TIMEOUT_SEC = 20
WATCHDOG_RETRY_LIMITS = {
    "artifacts/analysis.md": 1,
    "artifacts/file_request.json": 2,
    "artifacts/context_pack.json": 2,
    "artifacts/PLAN_draft.md": 2,
    "artifacts/PLAN.md": 2,
    "reviews/review_contract.md": 1,
    "reviews/review_cost.md": 1,
}


def parse_iso(value: str) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def seconds_since_iso(value: str, *, now_ts: str) -> int | None:
    then = parse_iso(value)
    now = parse_iso(now_ts)
    if then is None or now is None:
        return None
    return max(0, int((now - then).total_seconds()))


def later_iso(*values: str) -> str:
    best = ""
    best_dt: dt.datetime | None = None
    for raw in values:
        text = str(raw or "").strip()
        parsed = parse_iso(text)
        if parsed is None:
            continue
        if best_dt is None or parsed > best_dt:
            best_dt = parsed
            best = text
    return best


def expected_artifact_rel(gate: dict[str, Any]) -> str:
    path = str(gate.get("path", "")).strip()
    if not path:
        return ""
    first = path.split("|", 1)[0].strip()
    if not first or first.startswith("http"):
        return ""
    if first.startswith("artifacts/") or first.startswith("reviews/"):
        return first
    return ""


def expected_artifact_abs(run_dir: Path, rel_path: str, *, is_within: Callable[[Path, Path], bool]) -> Path | None:
    rel = str(rel_path or "").strip()
    if not rel:
        return None
    candidate = (run_dir / Path(rel)).resolve()
    if not is_within(candidate, run_dir):
        return None
    return candidate


def gate_max_retries(gate: dict[str, Any]) -> int:
    rel = expected_artifact_rel(gate)
    if not rel:
        return 0
    if rel in WATCHDOG_RETRY_LIMITS:
        return int(WATCHDOG_RETRY_LIMITS[rel])
    return 1


def gate_recovery_action(gate: dict[str, Any]) -> str:
    rel = expected_artifact_rel(gate)
    if not rel:
        return "reconcile latest gate truth and inspect orchestrator/provider evidence"
    name = Path(rel).name
    if name == "PLAN_draft.md":
        return "retry planner and verify PLAN_draft.md lands with a valid draft contract"
    if name == "PLAN.md":
        return "sign and materialize PLAN.md from the approved draft"
    if name == "context_pack.json":
        return "retry librarian context generation and verify context_pack.json lands"
    if name == "file_request.json":
        return "retry planner intake synthesis and verify file_request.json lands"
    if name == "output_contract_freeze.json":
        return "rerun contract freezing and verify output_contract_freeze.json lands with a valid project output contract"
    if name == "source_generation_report.json":
        return "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes"
    if name == "docs_generation_report.json":
        return "regenerate docs outputs and verify docs_generation_report.json passes the project-generation gate"
    if name == "workflow_generation_report.json":
        return "regenerate workflow outputs and verify workflow_generation_report.json passes the project-generation gate"
    if name == "project_manifest.json":
        return "repair manifest fields and regenerate project_manifest.json so deliver/verify can continue"
    if name == "deliverable_index.json":
        return "repair deliverable index contents and regenerate deliverable_index.json so verify can continue"
    if name.startswith("review_"):
        return f"rerun the review step and verify {name} lands"
    return f"rerun the producer for {name} and verify it lands"


def is_waiting_reason(text: str) -> bool:
    return str(text or "").strip().lower().startswith("waiting for ")


def is_executed_target_missing_reason(text: str) -> bool:
    return "provider reported executed but target missing" in str(text or "").strip().lower()


def runtime_progress_marker_iso(
    run_dir: Path,
    expected_artifact_rel_path: str,
    *,
    file_ts_iso: Callable[[Path], str],
    is_within: Callable[[Path, Path], bool],
) -> str:
    markers: list[str] = []
    for rel in ("step_meta.jsonl", "events.jsonl"):
        path = run_dir / rel
        if path.exists():
            markers.append(file_ts_iso(path))
    artifact = expected_artifact_abs(run_dir, expected_artifact_rel_path, is_within=is_within)
    if artifact is not None and artifact.exists():
        markers.append(file_ts_iso(artifact))
    return later_iso(*markers)


def gate_watchdog_doc(
    run_dir: Path,
    previous_state: dict[str, Any],
    gate: dict[str, Any],
    *,
    now_ts: str,
    is_within: Callable[[Path, Path], bool],
    file_ts_iso: Callable[[Path], str],
) -> dict[str, Any]:
    prev_gate = previous_state.get("gate", {}) if isinstance(previous_state.get("gate", {}), dict) else {}
    path = str(gate.get("path", "")).strip()
    reason = str(gate.get("reason", "")).strip()
    owner = str(gate.get("owner", "")).strip()
    same_gate = (
        str(prev_gate.get("path", "")).strip() == path
        and str(prev_gate.get("reason", "")).strip() == reason
        and str(prev_gate.get("owner", "")).strip() == owner
    )
    expected_artifact = expected_artifact_rel(gate)
    expected_abs = expected_artifact_abs(run_dir, expected_artifact, is_within=is_within)
    expected_exists = bool(expected_abs and expected_abs.exists())
    entered_at = str(prev_gate.get("entered_at", "")).strip() if same_gate else ""
    if not entered_at:
        entered_at = now_ts
    progress_marker_at = runtime_progress_marker_iso(
        run_dir,
        expected_artifact,
        file_ts_iso=file_ts_iso,
        is_within=is_within,
    )
    updated_at = later_iso(
        str(prev_gate.get("updated_at", "")).strip() if same_gate else "",
        progress_marker_at,
        entered_at,
    ) or now_ts
    retry_count = int(prev_gate.get("retry_count", 0) or 0) if same_gate else 0
    max_retries = int(prev_gate.get("max_retries", 0) or 0) if same_gate else gate_max_retries(gate)
    last_retry_at = str(prev_gate.get("last_retry_at", "")).strip() if same_gate else ""
    stalled_seconds = seconds_since_iso(updated_at, now_ts=now_ts) or 0
    gate_state = str(gate.get("state", "")).strip().lower()
    is_blocked = gate_state == "blocked"
    exec_failed = is_blocked and is_executed_target_missing_reason(reason)
    invalid_existing_artifact = bool(
        is_blocked
        and expected_artifact
        and expected_exists
        and reason
        and not is_waiting_reason(reason)
        and not exec_failed
    )
    stalled = bool(is_blocked and expected_artifact and (not expected_exists) and stalled_seconds >= WATCHDOG_STALL_TIMEOUT_SEC)
    watchdog_status = "waiting"
    if invalid_existing_artifact:
        watchdog_status = "blocked_hard"
    elif expected_artifact and expected_exists:
        watchdog_status = "satisfied"
    elif exec_failed:
        watchdog_status = "exec_failed"
    elif is_blocked and stalled and retry_count >= max_retries > 0:
        watchdog_status = "recovery_needed"
    elif is_blocked and stalled and retry_count < max_retries:
        watchdog_status = "retry_ready"
    elif is_blocked and retry_count > 0 and last_retry_at:
        watchdog_status = "retrying"
    elif is_blocked and not expected_artifact:
        watchdog_status = "blocked_hard"
    recovery_action = gate_recovery_action(gate)
    return {
        "entered_at": entered_at,
        "updated_at": updated_at,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "expected_artifact": expected_artifact,
        "expected_exists": expected_exists,
        "recovery_action": recovery_action,
        "last_retry_at": last_retry_at,
        "stalled": stalled,
        "stalled_seconds": stalled_seconds,
        "watchdog_status": watchdog_status,
    }


def retry_attempt_text(*, retry_count: int, max_retries: int, expected_artifact: str) -> str:
    target = Path(expected_artifact).name if expected_artifact else "目标产物"
    return f"已自动重试 {retry_count}/{max_retries} 次，目标仍是 {target}"


def watchdog_phase(gate: dict[str, Any]) -> str:
    watchdog_status = str(gate.get("watchdog_status", "")).strip().lower()
    if watchdog_status in {"retry_ready", "retrying"}:
        return "RETRYING"
    if watchdog_status == "recovery_needed":
        return "RECOVERY_NEEDED"
    if watchdog_status == "exec_failed":
        return "EXEC_FAILED"
    if watchdog_status == "blocked_hard":
        return "BLOCKED_HARD"
    return ""


def build_recovery_doc(
    *,
    final_ready: bool,
    submitted_open: list[dict[str, Any]],
    has_error: bool,
    gate_state: str,
    gate: dict[str, Any],
) -> dict[str, Any]:
    expected_artifact = str(gate.get("expected_artifact", "")).strip()
    recovery_action = str(gate.get("recovery_action", "")).strip()
    retry_count = int(gate.get("retry_count", 0) or 0)
    max_retries = int(gate.get("max_retries", 0) or 0)
    last_retry_at = str(gate.get("last_retry_at", "")).strip()
    watchdog_status = str(gate.get("watchdog_status", "")).strip().lower()
    retry_attempt = retry_attempt_text(
        retry_count=retry_count,
        max_retries=max_retries,
        expected_artifact=expected_artifact,
    ) if retry_count > 0 and max_retries > 0 else ""
    if final_ready:
        return {"needed": False, "hint": "", "status": "none", "retry_count": retry_count, "max_retries": max_retries}
    if submitted_open:
        return {
            "needed": True,
            "hint": "run ctcp_advance after decision consumption",
            "status": "required",
            "kind": "decision_consumption_followup",
            "last_attempt": "",
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action,
            "last_retry_at": last_retry_at,
        }
    if watchdog_status == "exec_failed":
        return {
            "needed": True,
            "hint": recovery_action or "provider reported executed but target missing; inspect the producer evidence and re-run the failed gate",
            "status": "exec_failed",
            "kind": "executed_target_missing",
            "last_attempt": retry_attempt,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action,
            "last_retry_at": last_retry_at,
        }
    if watchdog_status == "recovery_needed":
        return {
            "needed": True,
            "hint": recovery_action or "automatic retries are exhausted; switch to explicit recovery",
            "status": "recovery_needed",
            "kind": "retry_exhausted",
            "last_attempt": retry_attempt,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action,
            "last_retry_at": last_retry_at,
        }
    if watchdog_status == "blocked_hard":
        return {
            "needed": True,
            "hint": recovery_action or "reconcile latest gate truth and inspect backend evidence",
            "status": "blocked_hard",
            "kind": "non_retryable_block",
            "last_attempt": retry_attempt,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action,
            "last_retry_at": last_retry_at,
        }
    if watchdog_status in {"retry_ready", "retrying"}:
        return {
            "needed": True,
            "hint": recovery_action or "retry the stalled gate and verify the expected artifact lands",
            "status": watchdog_status,
            "kind": "stalled_waiting_gate",
            "last_attempt": retry_attempt,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action,
            "last_retry_at": last_retry_at,
        }
    if has_error:
        return {
            "needed": True,
            "hint": "inspect verify report and failure bundle",
            "status": "required",
            "kind": "failure_recovery",
            "last_attempt": "",
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action,
            "last_retry_at": last_retry_at,
        }
    if gate_state == "blocked" and "plan_draft.md" in str(gate.get("path", "")).strip().lower():
        return {
            "needed": True,
            "hint": "retry planner to generate PLAN_draft.md; if it stays missing, escalate to recoverable blocked status",
            "status": "retry_ready",
            "kind": "planner_retry",
            "last_attempt": "",
            "retry_count": retry_count,
            "max_retries": max_retries,
            "expected_artifact": expected_artifact,
            "recovery_action": recovery_action or gate_recovery_action(gate),
            "last_retry_at": last_retry_at,
        }
    return {
        "needed": False,
        "hint": "",
        "status": "none",
        "retry_count": retry_count,
        "max_retries": max_retries,
        "expected_artifact": expected_artifact,
        "recovery_action": recovery_action,
        "last_retry_at": last_retry_at,
    }


def build_error_doc(*, has_error: bool, run_status: str, gate_state: str, gate: dict[str, Any]) -> dict[str, Any]:
    watchdog_status = str(gate.get("watchdog_status", "")).strip().lower()
    return {
        "has_error": bool(has_error or watchdog_status in {"exec_failed", "blocked_hard"}),
        "code": (
            "exec_failed"
            if watchdog_status == "exec_failed"
            else ("blocked_hard" if watchdog_status == "blocked_hard" else (run_status if run_status in {"fail", "failed", "error", "aborted"} else (gate_state if gate_state in {"error", "failed"} else "")))
        ),
        "message": str(gate.get("reason", "")).strip() if (has_error or watchdog_status in {"exec_failed", "blocked_hard"}) else "",
    }


def load_verify_progress(
    run_dir: Path,
    previous_state: dict[str, Any],
    iterations: dict[str, Any],
    *,
    read_json: Callable[[Path], dict[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    verify_result = str(previous_state.get("verify_result", "")).strip().upper()
    verify_gate = str(previous_state.get("verify_gate", "")).strip().lower()
    if verify_doc := read_json(run_dir / "artifacts" / "verify_report.json"):
        verify_result = str(verify_doc.get("result", "")).strip().upper() or verify_result
        verify_gate = str(verify_doc.get("gate", "")).strip().lower() or verify_gate
        iterations["current"] = int(verify_doc.get("iteration", iterations.get("current", 0)) or 0)
        iterations["max"] = int(verify_doc.get("max_iterations", iterations.get("max", 0)) or 0)
        if verify_doc.get("max_iterations") is not None:
            iterations["source"] = str(iterations.get("source", "")).strip() or "verify_report.json"
    return verify_result, verify_gate, iterations


def runtime_blocking_reason(
    *,
    pending_user_decisions: list[dict[str, Any]],
    submitted_open: list[dict[str, Any]],
    has_error: bool,
    gate_state: str,
    gate: dict[str, Any],
    previous_state: dict[str, Any],
    run_status: str,
    final_ready: bool,
    running_statuses: set[str],
) -> str:
    run_status_l = str(run_status or "").strip().lower()
    if pending_user_decisions:
        first = pending_user_decisions[0]
        return str(first.get("question", "") or first.get("reason", "")).strip() or str(gate.get("reason", "")).strip() or "decision_required"
    if submitted_open:
        return "decision_submitted_waiting_backend_consume"
    if has_error:
        return str(gate.get("reason", "")).strip() or f"run_status={run_status or 'error'}"
    if gate_state == "blocked":
        return str(gate.get("reason", "")).strip() or str(previous_state.get("blocking_reason", "")).strip() or "blocked"
    if final_ready or run_status_l in running_statuses or gate_state in {"open", "pass", "ready_apply", "ready_verify", "resolve_find_local"}:
        return "none"
    previous_reason = str(previous_state.get("blocking_reason", "")).strip()
    if previous_reason and previous_reason.lower() != "none" and run_status_l in {"blocked", "new", "created", "pending", "queued"}:
        return previous_reason
    return "none" if final_ready else "none"


def mark_retry_attempt(
    run_dir: Path,
    runtime_state: dict[str, Any],
    *,
    now_utc_iso: Callable[[], str],
    write_runtime_state: Callable[[Path, dict[str, Any]], None],
    append_event: Callable[..., None],
) -> dict[str, Any]:
    gate = dict(runtime_state.get("gate", {}) if isinstance(runtime_state.get("gate", {}), dict) else {})
    if str(gate.get("watchdog_status", "")).strip().lower() != "retry_ready":
        return runtime_state
    now_ts = now_utc_iso()
    expected_artifact = str(gate.get("expected_artifact", "")).strip()
    max_retries = int(gate.get("max_retries", 0) or 0)
    retry_count = int(gate.get("retry_count", 0) or 0) + 1
    gate["retry_count"] = retry_count
    gate["last_retry_at"] = now_ts
    gate["updated_at"] = now_ts
    gate["watchdog_status"] = "retrying"
    recovery = dict(runtime_state.get("recovery", {}) if isinstance(runtime_state.get("recovery", {}), dict) else {})
    recovery["needed"] = True
    recovery["status"] = "retrying"
    recovery["hint"] = str(gate.get("recovery_action", "")).strip() or gate_recovery_action(gate)
    recovery["last_attempt"] = retry_attempt_text(
        retry_count=retry_count,
        max_retries=max_retries,
        expected_artifact=expected_artifact,
    ) if max_retries > 0 else ""
    recovery["retry_count"] = retry_count
    recovery["max_retries"] = max_retries
    recovery["expected_artifact"] = expected_artifact
    recovery["recovery_action"] = str(gate.get("recovery_action", "")).strip()
    recovery["last_retry_at"] = now_ts
    updated = dict(runtime_state)
    updated["phase"] = "RETRYING"
    updated["gate"] = gate
    updated["recovery"] = recovery
    updated["updated_at"] = now_ts
    write_runtime_state(run_dir, updated)
    append_event(
        run_dir,
        "WATCHDOG_AUTO_RETRY",
        expected_artifact,
        retry_count=retry_count,
        max_retries=max_retries,
        recovery_action=str(gate.get("recovery_action", "")).strip(),
    )
    return updated


def normalize_decision_registry_after_error(decision_registry: list[dict[str, Any]], *, now_ts: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_registry: list[dict[str, Any]] = []
    for row in decision_registry:
        if not isinstance(row, dict):
            continue
        current = dict(row)
        if str(current.get("status", "")).strip().lower() == "submitted":
            current["status"] = "consumed"
            current["consumed_at"] = str(current.get("consumed_at", "")).strip() or now_ts
        normalized_registry.append(current)
    return normalized_registry, [], []


def build_runtime_snapshot(
    *,
    run_dir: Path,
    phase: str,
    run_status: str,
    blocking_reason: str,
    needs_user_decision: bool,
    open_decisions: list[dict[str, Any]],
    decision_registry: list[dict[str, Any]],
    decision_source: str,
    legacy_fallback_used: bool,
    latest_result: dict[str, Any],
    error_doc: dict[str, Any],
    recovery_doc: dict[str, Any],
    gate: dict[str, Any],
    iterations: dict[str, Any],
    verify_result: str,
    verify_gate: str,
    submitted_open: list[dict[str, Any]],
    now_ts: str,
    runtime_core_hash: Callable[[dict[str, Any]], str],
    run_id_from_dir: Callable[[Path], str],
) -> dict[str, Any]:
    core_hash = runtime_core_hash(
        {
            "run_status": run_status,
            "verify_result": verify_result,
            "verify_gate": verify_gate,
            "gate": gate,
            "iterations": iterations,
            "latest_status_raw": latest_result.get("status_raw", {}),
            "decisions": decision_registry,
        }
    )
    return {
        "schema_version": "ctcp-support-runtime-state-v1",
        "run_id": run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "phase": phase,
        "run_status": run_status,
        "blocking_reason": blocking_reason or "none",
        "needs_user_decision": bool(needs_user_decision),
        "pending_decisions": open_decisions[:32],
        "decisions": decision_registry[:64],
        "decision_source": decision_source,
        "legacy_decision_fallback_used": legacy_fallback_used,
        "latest_result": latest_result,
        "error": error_doc,
        "recovery": recovery_doc,
        "gate": gate,
        "iterations": iterations,
        "verify_result": verify_result,
        "verify_gate": verify_gate,
        "decisions_needed_count": len([row for row in open_decisions if str(dict(row).get("status", "")).strip().lower() == "pending"]),
        "open_decisions_count": len(open_decisions),
        "submitted_decisions_count": len(submitted_open),
        "core_hash": core_hash,
        "updated_at": now_ts,
        "snapshot_source": "backend_interface_snapshot",
    }
