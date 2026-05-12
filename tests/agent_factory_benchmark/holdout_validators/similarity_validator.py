from __future__ import annotations

from typing import Any

from tests.agent_factory_benchmark.holdout_validators.common import agent_names, result, tool_names


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    if not context:
        return []
    current_id = str(fixture.get("case_id", ""))
    outputs = context.get("holdout_outputs", {})
    tools = tool_names(output)
    agents = agent_names(output)
    high_similarity = 0
    near_identical = 0
    for other_id, other in outputs.items():
        if other_id == current_id:
            continue
        tool_score = _jaccard(tools, tool_names(other))
        agent_score = _jaccard(agents, agent_names(other))
        if tool_score >= 0.85 or agent_score >= 0.85:
            high_similarity += 1
        if tool_score >= 0.95 and agent_score >= 0.95:
            near_identical += 1
    return [
        result(
            "holdout_similarity",
            "not_near_identical_to_all_holdouts",
            near_identical < max(1, len(outputs) - 2),
            f"near_identical_pairs={near_identical}",
        ),
        result(
            "holdout_similarity",
            "tool_or_agent_similarity_warning",
            high_similarity < max(2, len(outputs) // 2),
            f"high_similarity_pairs={high_similarity}",
            "warning",
        ),
    ]
