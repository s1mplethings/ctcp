from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .runtime_tool_executor import execute_tool_decision
from .runtime_tool_registry import normalize_tool_contract


DEFAULT_MAX_STEPS = 5


def planner_mode() -> str:
    return os.environ.get("CTCP_AGENT_PLANNER", "deterministic").strip().lower() or "deterministic"


def planner_max_steps() -> int:
    raw = os.environ.get("CTCP_AGENT_MAX_STEPS", "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_STEPS
    return max(1, min(20, value))


def _text(payload: dict[str, Any]) -> str:
    return " ".join(str(value) for value in payload.values() if isinstance(value, str)).lower()


def _has_tool(tool_defs: dict[str, dict[str, Any]], name: str) -> bool:
    return name in tool_defs


def _first_available(tool_defs: dict[str, dict[str, Any]], names: list[str]) -> str:
    for name in names:
        if _has_tool(tool_defs, name):
            return name
    return ""


def _dedupe(names: list[str]) -> list[str]:
    out: list[str] = []
    for name in names:
        if name and name not in out:
            out.append(name)
    return out


def _workflow_tools(workflow: dict[str, Any]) -> list[str]:
    return [str(name) for name in workflow.get("tools_called", []) if str(name)]


def _deterministic_actions(
    manifest: dict[str, Any],
    workflow: dict[str, Any],
    selected_agent: str,
    payload: dict[str, Any],
    tool_defs: dict[str, dict[str, Any]],
) -> list[str]:
    del manifest, selected_agent
    body = _text(payload)
    workflow_tools = _workflow_tools(workflow)
    if "unsupported synthetic" in body or "unknown synthetic" in body:
        return workflow_tools
    if _has_tool(tool_defs, "web_search"):
        return _dedupe(
            [
                "web_search",
                "fetch_url" if _has_tool(tool_defs, "fetch_url") else "",
                _first_available(tool_defs, ["source_summary", "summarize_text"]),
                _first_available(tool_defs, ["citation_builder", "create_draft"]),
            ]
        )
    if any(term in body for term in ("ignore all approvals", "refund", "rollback", "liability", "compensation")):
        return _dedupe(
            [
                _first_available(tool_defs, ["logs.query", "classify_input"]),
                _first_available(tool_defs, ["production.rollback.request", "refund.request"]),
                _first_available(tool_defs, ["refund.request", "external_legal_statement.request"]),
                _first_available(tool_defs, ["slack.draft", "customer.reply.draft", "create_draft"]),
            ]
        )
    if any(term in body for term in ("incident", "outage", "production", "rollback")):
        return _dedupe(
            [
                _first_available(tool_defs, ["logs.query", "classify_input"]),
                _first_available(tool_defs, ["metrics.query", "extract_fields"]),
                _first_available(tool_defs, ["slack.draft", "postmortem.write", "create_draft"]),
                _first_available(tool_defs, ["production.rollback.request", "production.config.change.request"]),
            ]
        )
    if any(term in body for term in ("feedback", "weekly report", "trend", "用户反馈", "周报")):
        return _dedupe(
            [
                _first_available(tool_defs, ["feedback.collect", "extract_fields"]),
                _first_available(tool_defs, ["feedback.classify", "classify_input"]),
                _first_available(tool_defs, ["feedback.trend.summarize", "summarize_text"]),
                _first_available(tool_defs, ["weekly_report.write", "create_draft"]),
            ]
        )
    if any(term in body for term in ("support", "customer", "reply", "issue")):
        return _dedupe(
            [
                _first_available(tool_defs, ["support.intake", "extract_fields"]),
                _first_available(tool_defs, ["support.classify", "classify_input"]),
                _first_available(tool_defs, ["customer.reply.draft", "create_draft"]),
            ]
        )
    if workflow_tools:
        return workflow_tools
    if _has_tool(tool_defs, "noop_response"):
        return ["noop_response"]
    return []


def _sources(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _approval_row(tool: dict[str, Any], agent: str, reason: str) -> dict[str, Any]:
    return {"tool": str(tool.get("tool_name", "")), "agent": agent, "reason": reason, "status": "pending_approval"}


def _blocked_row(tool: dict[str, Any], agent: str, reason: str) -> dict[str, Any]:
    return {"tool": str(tool.get("tool_name", "")), "agent": agent, "reason": reason, "status": "blocked"}


def _final_answer(
    *,
    selected_agent: str,
    results: list[dict[str, Any]],
    tool_defs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    del selected_agent
    sources = _sources(results)
    executed = [str(row.get("tool_name", "")) for row in results if row.get("status") == "executed"]
    pending: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for result in results:
        tool_name = str(result.get("tool_name", ""))
        tool = tool_defs.get(tool_name, normalize_tool_contract({"tool_name": tool_name}))
        reason = str(result.get("reason", ""))
        if result.get("status") == "pending_approval":
            pending.append(_approval_row(tool, str(result.get("agent", "")), reason))
        elif result.get("status") in {"blocked", "failed", "unsupported"}:
            blocked.append(_blocked_row(tool, str(result.get("agent", "")), reason))
            if tool.get("requires_approval") is True:
                pending.append(_approval_row(tool, str(result.get("agent", "")), "requires_approval"))
    if sources:
        text = "Completed the requested research summary with cited sources."
    elif pending or blocked:
        names = sorted({row["tool"] for row in pending + blocked if row.get("tool")})
        text = "Completed safe planner steps. Blocked or approval-required actions were not executed: " + ", ".join(names)
    else:
        text = "Completed the requested task with deterministic local tools."
    return {
        "text": text,
        "sources": sources,
        "pending_approvals": pending,
        "blocked_tools": blocked,
        "executed_tools": executed,
    }


def _trace_step(
    *,
    step_index: int,
    mode: str,
    decision: str,
    tool_name: str = "",
    reason: str,
    tool_input: dict[str, Any] | None = None,
    observed_result_status: str = "",
) -> dict[str, Any]:
    return {
        "step_index": step_index,
        "planner_mode": mode,
        "decision": decision,
        "tool_name": tool_name,
        "reason": reason,
        "input": tool_input or {},
        "observed_result_status": observed_result_status,
    }


def write_planner_trace(root: Path, trace: list[dict[str, Any]]) -> Path:
    path = root / "planner_trace.json"
    path.write_text(json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_planner_loop(
    root: Path,
    *,
    manifest: dict[str, Any],
    workflow: dict[str, Any],
    selected_agent: str,
    payload: dict[str, Any],
    tool_defs: dict[str, dict[str, Any]],
    current_state: str,
) -> dict[str, Any]:
    mode = planner_mode()
    max_steps = planner_max_steps()
    trace: list[dict[str, Any]] = []
    if mode == "provider":
        trace.append(_trace_step(step_index=1, mode=mode, decision="stop", reason="provider_planner_unavailable"))
        write_planner_trace(root, trace)
        return {
            "planner_mode": mode,
            "status": "failed",
            "reason": "provider_planner_unavailable",
            "tool_results": [],
            "planner_trace": trace,
            "final_answer": {"text": "Provider planner is not configured.", "sources": [], "pending_approvals": [], "blocked_tools": [], "executed_tools": []},
            "planner_trace_path": "planner_trace.json",
        }
    if mode != "deterministic":
        trace.append(_trace_step(step_index=1, mode=mode, decision="stop", reason="unsupported_planner_mode"))
        write_planner_trace(root, trace)
        return {
            "planner_mode": mode,
            "status": "failed",
            "reason": "unsupported_planner_mode",
            "tool_results": [],
            "planner_trace": trace,
            "final_answer": {"text": "Planner mode is unsupported.", "sources": [], "pending_approvals": [], "blocked_tools": [], "executed_tools": []},
            "planner_trace_path": "planner_trace.json",
        }

    actions = _deterministic_actions(manifest, workflow, selected_agent, payload, tool_defs)
    results: list[dict[str, Any]] = []
    action_index = 0
    final_answer: dict[str, Any] | None = None
    for step_index in range(1, max_steps + 1):
        if action_index >= len(actions):
            final_answer = _final_answer(selected_agent=selected_agent, results=results, tool_defs=tool_defs)
            trace.append(_trace_step(step_index=step_index, mode=mode, decision="final_answer", reason="planner_completed", observed_result_status=""))
            break
        tool_name = actions[action_index]
        action_index += 1
        tool = tool_defs.get(tool_name, normalize_tool_contract({"tool_name": tool_name}))
        result = execute_tool_decision(root, agent=selected_agent, tool=tool, tool_input=payload, context={"workflow_state": current_state, "previous_results": results})
        result["agent"] = selected_agent
        results.append(result)
        trace.append(
            _trace_step(
                step_index=step_index,
                mode=mode,
                decision="call_tool",
                tool_name=tool_name,
                reason="deterministic_action_selection",
                tool_input=payload,
                observed_result_status=str(result.get("status", "")),
            )
        )
    if final_answer is None:
        write_planner_trace(root, trace)
        return {
            "planner_mode": mode,
            "status": "failed",
            "reason": "planner_max_steps_exceeded",
            "tool_results": results,
            "planner_trace": trace,
            "final_answer": _final_answer(selected_agent=selected_agent, results=results, tool_defs=tool_defs),
            "planner_trace_path": "planner_trace.json",
        }
    first_failed_reason = next((str(row.get("reason", "")) for row in results if row.get("status") == "failed"), "")
    web_used = any(row.get("status") == "executed" and row.get("tool_name") in {"web_search", "fetch_url"} for row in results)
    if first_failed_reason == "missing_sources":
        status = "failed"
        reason = "missing_sources"
    elif first_failed_reason:
        status = "failed"
        reason = first_failed_reason
    elif web_used and not final_answer.get("sources"):
        status = "failed"
        reason = "missing_sources"
    else:
        status = "completed"
        reason = "planner_completed"
    write_planner_trace(root, trace)
    return {
        "planner_mode": mode,
        "status": status,
        "reason": reason,
        "tool_results": results,
        "planner_trace": trace,
        "final_answer": final_answer,
        "planner_trace_path": "planner_trace.json",
    }
