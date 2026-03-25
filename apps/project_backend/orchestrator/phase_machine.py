from __future__ import annotations

from contracts.enums import JobPhase


def phase_from_bridge_status(status_doc: dict[str, object]) -> JobPhase:
    run_status = str(status_doc.get("run_status", "")).strip().lower()
    gate_state = str(dict(status_doc.get("gate", {}) or {}).get("state", "")).strip().lower()
    verify_result = str(status_doc.get("verify_result", "")).strip().upper()

    if verify_result == "PASS" or run_status in {"pass", "done", "completed"}:
        return JobPhase.DONE
    if run_status == "fail":
        return JobPhase.FAILED
    if bool(status_doc.get("needs_user_decision", False)):
        return JobPhase.WAITING_ANSWER
    if gate_state in {"ready_verify", "verify", "verification"}:
        return JobPhase.VERIFICATION
    if gate_state in {"blocked", "blocked_needs_input"}:
        return JobPhase.REPAIR
    return JobPhase.GENERATION
