from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runtime_audit import write_event
from .runtime_planner import run_planner_loop
from .runtime_state import append_unique, load_state, save_state
from .runtime_tool_policy import can_execute_tool
from .runtime_tool_registry import build_tool_registry, normalize_tool_contract, supported_local_tool_names, supported_web_tool_names


REQUIRED_TOP_LEVEL_FIELDS = (
    "manifest_version",
    "system_name",
    "agents",
    "tools",
    "workflows",
    "memory",
    "permissions",
    "guardrails",
    "test_cases",
)

RUNTIME_STATES = {"entry", "processing", "waiting_approval", "completed", "blocked", "failed"}


def load_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in manifest]
    if missing:
        raise ValueError(f"manifest missing required fields: {', '.join(missing)}")
    return manifest


def load_input(input_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"input is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    return payload


def _first_agent(manifest: dict[str, Any]) -> str:
    agents = manifest.get("agents") or []
    if agents and isinstance(agents[0], dict):
        return str(agents[0].get("name", ""))
    return ""


def _workflow_by_name(manifest: dict[str, Any], name: str) -> dict[str, Any] | None:
    for workflow in manifest.get("workflows", []):
        if isinstance(workflow, dict) and workflow.get("state_name") == name:
            return workflow
    return None


def _entry_workflow(manifest: dict[str, Any]) -> dict[str, Any]:
    workflows = [item for item in manifest.get("workflows", []) if isinstance(item, dict)]
    if not workflows:
        return {"state_name": "entry", "responsible_agent": _first_agent(manifest), "tools_called": [], "next_states": []}
    return workflows[0]


def _request_text(payload: dict[str, Any]) -> str:
    return " ".join(str(value) for value in payload.values() if isinstance(value, str)).lower()


def _select_workflow(manifest: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    text = _request_text(payload)
    workflows = [item for item in manifest.get("workflows", []) if isinstance(item, dict)]
    best: tuple[int, dict[str, Any] | None] = (0, None)
    for workflow in workflows:
        haystack = " ".join(
            [
                str(workflow.get("state_name", "")),
                str(workflow.get("trigger", "")),
                " ".join(str(action) for action in workflow.get("actions", [])),
                " ".join(str(tool) for tool in workflow.get("tools_called", [])),
            ]
        ).lower().replace("_", " ")
        score = sum(1 for word in set(text.split()) if len(word) > 3 and word in haystack)
        if score > best[0]:
            best = (score, workflow)
    return best[1] or _entry_workflow(manifest)


def _tool_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return build_tool_registry(manifest)


def _collect_sources(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for result in results:
        output = result.get("output") or {}
        if not isinstance(output, dict):
            continue
        for source in output.get("sources", []) or []:
            if isinstance(source, dict) and source.get("url") and source not in sources:
                sources.append(source)
        source = output.get("source")
        if isinstance(source, dict) and source.get("url") and source not in sources:
            sources.append(source)
    return sources


def _fallback_tool(tool_name: str) -> dict[str, Any]:
    if tool_name in {"web_search", "fetch_url"}:
        return normalize_tool_contract({"tool_name": tool_name, "runtime_adapter": tool_name})
    return normalize_tool_contract({"tool_name": tool_name})


def _approval_row(tool: dict[str, Any], agent: str, reason: str) -> dict[str, Any]:
    return {"tool": str(tool.get("tool_name", "")), "agent": agent, "reason": reason, "status": "pending_approval"}


def _blocked_row(tool: dict[str, Any], agent: str, reason: str) -> dict[str, Any]:
    return {"tool": str(tool.get("tool_name", "")), "agent": agent, "reason": reason, "status": "blocked"}


def _unsupported_row(tool: dict[str, Any], agent: str, reason: str) -> dict[str, Any]:
    return {"tool": str(tool.get("tool_name", "")), "agent": agent, "reason": reason, "status": "unsupported"}


def _final_answer_from_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": "Runtime is waiting for required approvals before continuing.",
        "sources": [],
        "pending_approvals": state.get("pending_approvals", []),
        "blocked_tools": state.get("blocked_tools", []),
        "executed_tools": [],
    }


def _preview(manifest: dict[str, Any], selected_agent: str, workflow: dict[str, Any]) -> dict[str, Any]:
    available: list[str] = []
    blocked: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for tool in build_tool_registry(manifest).values():
        decision = can_execute_tool(selected_agent, tool, "run", {})
        name = str(tool.get("tool_name", ""))
        if decision["status"] == "executed":
            available.append(name)
        elif decision["status"] == "pending_approval":
            pending.append(_approval_row(tool, selected_agent, decision["reason"]))
        elif decision["status"] == "unsupported":
            unsupported.append(_unsupported_row(tool, selected_agent, decision["reason"]))
            blocked.append(_blocked_row(tool, selected_agent, decision["reason"]))
            if tool.get("requires_approval") is True:
                pending.append(_approval_row(tool, selected_agent, "requires_approval"))
        else:
            blocked.append(_blocked_row(tool, selected_agent, decision["reason"]))
            if tool.get("requires_approval") is True:
                pending.append(_approval_row(tool, selected_agent, "requires_approval"))
    return {
        "available_tools": available,
        "blocked_tools": blocked,
        "pending_approvals": pending,
        "unsupported_tools": unsupported,
    }


def dry_run(root: Path, input_path: Path) -> dict[str, Any]:
    manifest = load_manifest(root)
    payload = load_input(input_path)
    workflow = _select_workflow(manifest, payload)
    selected_agent = str(workflow.get("responsible_agent") or _first_agent(manifest))
    preview = _preview(manifest, selected_agent, workflow)
    return {
        "mode": "dry-run",
        "status": "ok",
        "selected_agent": selected_agent,
        "workflow_entry_state": str(workflow.get("state_name", "entry")),
        "workflow_start": str(workflow.get("state_name", "entry")),
        "available_tools": preview["available_tools"],
        "tools_available": preview["available_tools"],
        "blocked_tools": preview["blocked_tools"],
        "pending_approvals": preview["pending_approvals"],
        "unsupported_tools": preview["unsupported_tools"],
        "pending_approval_tools": [row["tool"] for row in preview["pending_approvals"]],
        "approval_required_actions": manifest.get("permissions", {}).get("approval_required_for", []),
        "audit_log_required": bool(manifest.get("permissions", {}).get("audit_log_required", True)),
        "guardrails_active": manifest.get("guardrails", []),
        "supported_local_tools": supported_local_tool_names(),
        "supported_web_tools": supported_web_tool_names(),
        "input_path": str(input_path),
    }


def _next_workflow_state(workflow: dict[str, Any]) -> str:
    next_states = workflow.get("next_states") or []
    if next_states:
        return str(next_states[0])
    return "completed"


def run(root: Path, input_path: Path) -> dict[str, Any]:
    manifest = load_manifest(root)
    payload = load_input(input_path)
    initial_workflow = _select_workflow(manifest, payload)
    initial_agent = str(initial_workflow.get("responsible_agent") or _first_agent(manifest))
    state = load_state(root, initial_agent, str(initial_workflow.get("state_name", "entry")))
    current_state = str(state.get("current_workflow_state") or initial_workflow.get("state_name", "entry"))
    if current_state in {"waiting_approval", "blocked"} and state.get("pending_approvals"):
        write_event(root, "approval_required", agent=str(state.get("current_agent") or initial_agent), status="pending_approval", details={"pending_approvals": state.get("pending_approvals", [])})
        return {
            "mode": "run",
            "status": "blocked",
            "selected_agent": str(state.get("current_agent") or initial_agent),
            "workflow_state": current_state,
            "executed_tools": [],
            "blocked_tools": state.get("blocked_tools", []),
            "pending_approvals": state.get("pending_approvals", []),
            "unsupported_tools": state.get("unsupported_tools", []),
            "tool_results": [],
            "planner_mode": str(state.get("planner", {}).get("mode", "deterministic")) if isinstance(state.get("planner"), dict) else "deterministic",
            "planner_trace_path": str(state.get("planner", {}).get("trace_path", "planner_trace.json")) if isinstance(state.get("planner"), dict) else "planner_trace.json",
            "final_answer": _final_answer_from_state(state),
            "guardrails_active": manifest.get("guardrails", []),
            "audit_log_path": "audit/events.jsonl",
            "runtime_state_path": "runtime_state.json",
        }

    workflow = _workflow_by_name(manifest, current_state) or initial_workflow
    selected_agent = str(workflow.get("responsible_agent") or state.get("current_agent") or initial_agent)
    tool_defs = _tool_map(manifest)
    tool_names = [str(name) for name in workflow.get("tools_called", [])]
    if not tool_names:
        tool_names = ["noop_response"]
        tool_defs["noop_response"] = normalize_tool_contract({"tool_name": "noop_response", "side_effect_level": "none", "requires_approval": False, "allowed_callers": [selected_agent]})

    planner_result = run_planner_loop(
        root,
        manifest=manifest,
        workflow=workflow,
        selected_agent=selected_agent,
        payload=payload,
        tool_defs=tool_defs,
        current_state=current_state,
    )
    executed: list[str] = []
    blocked: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = list(planner_result.get("tool_results", []))
    for result in results:
        tool_name = str(result.get("tool_name", ""))
        tool = tool_defs.get(tool_name, _fallback_tool(tool_name))
        if result["status"] == "executed":
            executed.append(tool_name)
            append_unique(state["executed_tools"], tool_name)
        elif result["status"] == "failed":
            row = _blocked_row(tool, selected_agent, result["reason"])
            blocked.append(row)
            append_unique(state["blocked_tools"], row)
        elif result["status"] == "pending_approval":
            row = _approval_row(tool, selected_agent, result["reason"])
            pending.append(row)
            append_unique(state["pending_approvals"], row)
        elif result["status"] == "unsupported":
            row = _unsupported_row(tool, selected_agent, result["reason"])
            unsupported.append(row)
            append_unique(state["unsupported_tools"], row)
            blocked_row = _blocked_row(tool, selected_agent, result["reason"])
            blocked.append(blocked_row)
            append_unique(state["blocked_tools"], blocked_row)
        else:
            row = _blocked_row(tool, selected_agent, result["reason"])
            blocked.append(row)
            append_unique(state["blocked_tools"], row)
            if tool.get("requires_approval") is True:
                approval = _approval_row(tool, selected_agent, "requires_approval")
                pending.append(approval)
                append_unique(state["pending_approvals"], approval)

    previous = current_state
    failed = planner_result.get("status") == "failed" or any(result.get("status") == "failed" for result in results)
    if failed:
        next_state = "failed"
        status = "failed"
    elif blocked or pending:
        next_state = "waiting_approval"
        status = "blocked"
    else:
        next_state = _next_workflow_state(workflow)
        status = "completed"
    append_unique(state["completed_steps"], previous)
    state["current_agent"] = selected_agent
    state["current_workflow_state"] = next_state
    state["last_tool_results"] = results
    state["planner"] = {
        "mode": planner_result.get("planner_mode", "deterministic"),
        "trace_path": planner_result.get("planner_trace_path", "planner_trace.json"),
        "step_count": len(planner_result.get("planner_trace", [])),
        "status": planner_result.get("status", status),
        "reason": planner_result.get("reason", ""),
    }
    save_state(root, state)
    write_event(root, "workflow_transition", agent=selected_agent, tool="", status=status, details={"from": previous, "to": next_state, "planner_mode": planner_result.get("planner_mode", "deterministic")})

    return {
        "mode": "run",
        "status": status,
        "reason": planner_result.get("reason", status),
        "selected_agent": selected_agent,
        "planner_mode": planner_result.get("planner_mode", "deterministic"),
        "planner_trace_path": planner_result.get("planner_trace_path", "planner_trace.json"),
        "final_answer": planner_result.get("final_answer", _final_answer_from_state(state)),
        "workflow_state": next_state,
        "executed_tools": executed,
        "blocked_tools": blocked,
        "pending_approvals": pending or state.get("pending_approvals", []),
        "unsupported_tools": unsupported or state.get("unsupported_tools", []),
        "tool_results": results,
        "sources": _collect_sources(results),
        "guardrails_active": manifest.get("guardrails", []),
        "audit_log_path": "audit/events.jsonl",
        "runtime_state_path": "runtime_state.json",
    }
