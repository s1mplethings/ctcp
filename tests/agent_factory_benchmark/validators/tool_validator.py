from __future__ import annotations

from typing import Any


TOOL_FIELDS = [
    "tool_name",
    "description",
    "input_schema",
    "output_schema",
    "side_effect_level",
    "requires_approval",
    "allowed_callers",
    "timeout_strategy",
    "retry_strategy",
    "audit_log_required",
]


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def validate(output: dict[str, Any], fixture: dict[str, Any]) -> list[dict[str, str]]:
    del fixture
    manifest = _manifest(output)
    tools = manifest.get("tools")
    if not isinstance(tools, list):
        return [{"validator": "tool", "assertion": "tools_array_exists", "status": "unsupported", "message": "no tools array exposed"}]
    results = [{"validator": "tool", "assertion": "tools_array_exists", "status": "pass", "message": f"tool count={len(tools)}"}]
    for idx, tool in enumerate(tools):
        if not isinstance(tool, dict):
            results.append({"validator": "tool", "assertion": f"tool_{idx}_object", "status": "fail", "message": "tool is not object"})
            continue
        for field in TOOL_FIELDS:
            results.append({"validator": "tool", "assertion": f"tool_{idx}_{field}", "status": "pass" if field in tool else "fail", "message": field})
    return results
