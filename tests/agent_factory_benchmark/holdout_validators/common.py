from __future__ import annotations

import json
from typing import Any


def manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).lower().replace("-", "_").replace(" ", "_")


def tool_names(doc: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for tool in manifest(doc).get("tools", []):
        if isinstance(tool, dict):
            names.add(str(tool.get("tool_name", "")).lower())
    return names


def agent_names(doc: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for agent in manifest(doc).get("agents", []):
        if isinstance(agent, dict):
            names.add(str(agent.get("name", "")).lower())
    return names


def workflow_names(doc: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    workflows = manifest(doc).get("workflows", manifest(doc).get("workflow", []))
    for state in workflows:
        if isinstance(state, dict):
            names.add(str(state.get("state_name", "")).lower())
    return names


def capability_blob(doc: dict[str, Any]) -> str:
    m = manifest(doc)
    agents = [
        {key: agent.get(key) for key in ("name", "role", "goal", "scope", "tools")}
        for agent in m.get("agents", [])
        if isinstance(agent, dict)
    ]
    tools = [
        {key: tool.get(key) for key in ("tool_name", "side_effect_level", "requires_approval")}
        for tool in m.get("tools", [])
        if isinstance(tool, dict)
    ]
    workflows = [
        {key: state.get(key) for key in ("state_name", "tools_called", "responsible_agent")}
        for state in m.get("workflows", m.get("workflow", []))
        if isinstance(state, dict)
    ]
    return blob({"agents": agents, "tools": tools, "workflows": workflows, "memory": m.get("memory", [])})


def result(validator: str, assertion: str, ok: bool, message: str, status_if_bad: str = "fail") -> dict[str, str]:
    return {
        "validator": validator,
        "assertion": assertion,
        "status": "pass" if ok else status_if_bad,
        "message": message,
    }
