from __future__ import annotations

from typing import Any


CRISIS_TOOL_TERMS = {"logs", "metrics", "deployment", "rollback", "postmortem", "production.config"}


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def _tool_set(manifest: dict[str, Any]) -> set[str]:
    tools = manifest.get("tools", [])
    names: set[str] = set()
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict):
                names.add(str(tool.get("tool_name", "")).lower())
    return names


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    manifest = _manifest(output)
    expectations = fixture.get("semantic_expectations", {})
    tools = _tool_set(manifest)
    results: list[dict[str, str]] = []
    if expectations.get("lightweight_case") or expectations.get("specific_case"):
        crisis_hits = sorted(tool for tool in tools if any(term in tool for term in CRISIS_TOOL_TERMS))
        results.append(
            {
                "validator": "semantic_overgeneration",
                "assertion": "no_crisis_toolkit_for_lightweight_or_specific_case",
                "status": "fail" if crisis_hits else "pass",
                "message": ", ".join(crisis_hits) or "no crisis toolkit",
            }
        )

    if expectations.get("prefer_single_agent"):
        agents = _manifest(output).get("agents", [])
        agent_count = len(agents) if isinstance(agents, list) else 0
        rationale = str(_manifest(output).get("planning_rationale", "")).lower()
        ok = agent_count <= 2 or "multi-agent" in rationale or "multi agent" in rationale
        results.append(
            {
                "validator": "semantic_overgeneration",
                "assertion": "single_agent_or_reasoned_multi_agent",
                "status": "pass" if ok else "fail",
                "message": f"agent_count={agent_count}",
            }
        )

    if context:
        current_id = str(fixture.get("case_id", ""))
        outputs = context.get("semantic_outputs", {})
        for other_id, other_output in outputs.items():
            if other_id <= current_id:
                continue
            other_tools = _tool_set(_manifest(other_output))
            score = _jaccard(tools, other_tools)
            if score > 0.75 and len(tools | other_tools) >= 4:
                results.append(
                    {
                        "validator": "semantic_overgeneration",
                        "assertion": f"tool_set_similarity_{other_id}",
                        "status": "warning",
                        "message": f"Jaccard similarity {score:.2f}",
                    }
                )
    return results
