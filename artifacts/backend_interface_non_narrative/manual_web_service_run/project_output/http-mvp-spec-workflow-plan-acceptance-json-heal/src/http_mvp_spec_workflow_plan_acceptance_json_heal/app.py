from __future__ import annotations

from .service_contract import build_contract
from .spec_builder import build_spec


def health_payload() -> dict[str, object]:
    return {"status": "ok", "archetype": "web_service"}


def generate_payload(goal: str, project_name: str) -> dict[str, object]:
    spec = build_spec(goal, project_name)
    return {
        "project_name": project_name,
        "goal_summary": spec.get("goal_summary", ""),
        "contract": [row.to_dict() for row in build_contract(spec)],
        "acceptance": list(spec.get("acceptance_criteria", [])),
    }
