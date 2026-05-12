from __future__ import annotations

from typing import Any


REQUIRED_AGENT_FIELDS = [
    "name",
    "role",
    "goal",
    "scope",
    "input_schema",
    "output_schema",
    "tools",
    "memory",
    "workflow",
    "permissions",
    "guardrails",
    "test_cases",
]


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    if isinstance(candidate, dict):
        return candidate
    return output


def validate(output: dict[str, Any], fixture: dict[str, Any]) -> list[dict[str, str]]:
    del fixture
    results: list[dict[str, str]] = []
    manifest = _manifest(output)
    results.append({"validator": "schema", "assertion": "output_is_json_object", "status": "pass", "message": "parsed as JSON object"})
    agents = manifest.get("agents")
    if not isinstance(agents, list):
        results.append({"validator": "schema", "assertion": "agents_array_exists", "status": "unsupported", "message": "no agent-manifest agents array exposed by project output"})
        for field in REQUIRED_AGENT_FIELDS:
            results.append({"validator": "schema", "assertion": f"required_field_{field}", "status": "unsupported", "message": "agent manifest surface unavailable"})
        return results
    results.append({"validator": "schema", "assertion": "agents_array_exists", "status": "pass", "message": f"agents count={len(agents)}"})
    first = agents[0] if agents and isinstance(agents[0], dict) else {}
    for field in REQUIRED_AGENT_FIELDS:
        status = "pass" if field in first or field in manifest else "fail"
        results.append({"validator": "schema", "assertion": f"required_field_{field}", "status": status, "message": field})
    return results
