from __future__ import annotations

from typing import Any

from tests.agent_factory_benchmark.holdout_validators.common import agent_names, capability_blob, result, tool_names


CRISIS_TERMS = ("rollback", "deployment", "incident", "postmortem", "refund", "billing", "external_legal")


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    del context
    expectations = fixture.get("holdout_expectations", {})
    if not expectations.get("lightweight_case"):
        return []
    tools = tool_names(output)
    agents = agent_names(output)
    blob = capability_blob(output)
    crisis_hits = sorted(term for term in CRISIS_TERMS if term in blob)
    results = [
        result(
            "holdout_minimality",
            "lightweight_case_no_crisis_stack",
            not crisis_hits,
            ", ".join(crisis_hits) or "no crisis stack",
        ),
        result(
            "holdout_minimality",
            "lightweight_case_tool_count",
            len(tools) <= 6,
            f"tool_count={len(tools)}",
            "warning",
        ),
        result(
            "holdout_minimality",
            "lightweight_case_agent_count",
            len(agents) <= 3,
            f"agent_count={len(agents)}",
            "warning",
        ),
    ]
    return results
