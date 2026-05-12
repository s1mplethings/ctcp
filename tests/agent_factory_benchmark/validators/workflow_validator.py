from __future__ import annotations

from typing import Any


WORKFLOW_FIELDS = ["trigger", "responsible_agent", "actions", "outputs", "next_states"]


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def validate(output: dict[str, Any], fixture: dict[str, Any]) -> list[dict[str, str]]:
    del fixture
    manifest = _manifest(output)
    workflows = manifest.get("workflows", manifest.get("workflow"))
    results: list[dict[str, str]] = []
    if isinstance(workflows, dict):
        workflows = [workflows]
    if not isinstance(workflows, list):
        return [{"validator": "workflow", "assertion": "workflow_exists", "status": "unsupported", "message": "no agent workflow section exposed"}]
    results.append({"validator": "workflow", "assertion": "workflow_exists", "status": "pass", "message": f"workflow count={len(workflows)}"})
    for idx, workflow in enumerate(workflows):
        if not isinstance(workflow, dict):
            results.append({"validator": "workflow", "assertion": f"workflow_{idx}_object", "status": "fail", "message": "workflow is not object"})
            continue
        for field in WORKFLOW_FIELDS:
            results.append({"validator": "workflow", "assertion": f"workflow_{idx}_{field}", "status": "pass" if field in workflow else "fail", "message": field})
        high_risk = any(token in str(workflow).lower() for token in ("rollback", "refund", "close issue", "legal", "compensation", "send email", "modify product"))
        if high_risk:
            approval = bool(workflow.get("human_approval_required", False)) or "approval" in str(workflow).lower()
            results.append({"validator": "workflow", "assertion": f"workflow_{idx}_high_risk_human_approval", "status": "pass" if approval else "fail", "message": "high-risk state approval"})
        results.append({"validator": "workflow", "assertion": f"workflow_{idx}_failure_paths", "status": "pass" if "failure_paths" in workflow else "fail", "message": "tool failure paths"})
    return results
