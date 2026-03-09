from __future__ import annotations

from typing import Any, Mapping


PRESENTATION_STATES = (
    "CREATED",
    "ANALYZING",
    "PLANNING",
    "WAITING_FOR_USER",
    "EXECUTING",
    "VERIFYING",
    "BLOCKED",
    "DONE",
)


def _str(doc: Mapping[str, Any], key: str) -> str:
    return str(doc.get(key, "")).strip()


def derive_presentation_state(status: Mapping[str, Any]) -> str:
    run_status = _str(status, "run_status").lower()
    verify_result = _str(status, "verify_result").upper()
    gate = status.get("gate", {})
    if not isinstance(gate, Mapping):
        gate = {}
    gate_state = _str(gate, "state").lower()
    gate_path = _str(gate, "path").lower()
    decisions_needed = int(status.get("decisions_needed_count", 0) or 0)

    if run_status == "pass" or verify_result == "PASS":
        return "DONE"
    if decisions_needed > 0:
        return "WAITING_FOR_USER"
    if run_status == "fail":
        return "BLOCKED"
    if gate_state == "ready_verify":
        return "VERIFYING"
    if gate_state in {"ready_apply", "resolve_find_local"}:
        return "EXECUTING"
    if gate_path.endswith("analysis.md") or gate_path.endswith("file_request.json") or gate_path.endswith("context_pack.json"):
        return "ANALYZING"
    if gate_path.endswith("plan_draft.md") or gate_path.endswith("plan.md") or "review_" in gate_path:
        return "PLANNING"
    if gate_state == "blocked":
        if run_status in {"running", "blocked"}:
            return "BLOCKED"
    if run_status in {"running", "blocked"}:
        return "CREATED"
    return "CREATED"


def render_progress_message(status: Mapping[str, Any], previous_state: str = "") -> str:
    state = derive_presentation_state(status)
    gate = status.get("gate", {})
    if not isinstance(gate, Mapping):
        gate = {}

    reason = _str(gate, "reason")
    owner = _str(gate, "owner")
    path = _str(gate, "path")
    decisions_count = int(status.get("decisions_needed_count", 0) or 0)

    if state == "DONE":
        return "The run is complete and CTCP reports verification passed. The final report is ready to review."
    if state == "WAITING_FOR_USER":
        return f"I’m currently waiting on {decisions_count} user decision item(s) from CTCP before I can continue execution."
    if state == "VERIFYING":
        return "CTCP is in verification stage now. I’ll report the result as soon as the gate finishes."
    if state == "EXECUTING":
        return "Execution is in progress. CTCP has moved past planning and is currently applying or advancing workflow steps."
    if state == "PLANNING":
        return "CTCP is preparing the plan/review stage. Once the plan artifacts are complete, execution can proceed."
    if state == "ANALYZING":
        return "CTCP is collecting and analyzing required context artifacts before planning."
    if state == "BLOCKED":
        if reason:
            if owner:
                return f"CTCP is blocked right now: {reason} (owner: {owner}, path: {path}). I can continue once this input is provided."
            return f"CTCP is blocked right now: {reason}. I can continue once this input is provided."
        return "CTCP is currently blocked and needs a missing input before it can continue."

    if previous_state and previous_state != state:
        return "A new run has been created and CTCP is starting initial analysis."
    return "A run is active. I’m tracking CTCP state and will keep translating progress into user-facing updates."
