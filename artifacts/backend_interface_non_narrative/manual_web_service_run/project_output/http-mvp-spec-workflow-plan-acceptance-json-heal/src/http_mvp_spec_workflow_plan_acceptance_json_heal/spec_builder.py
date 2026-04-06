from __future__ import annotations

from copy import deepcopy
from .seed import DEFAULT_PROJECT_INTENT, DEFAULT_PROJECT_SPEC


def build_spec(goal: str, project_name: str) -> dict[str, object]:
    spec = deepcopy(DEFAULT_PROJECT_SPEC)
    intent = deepcopy(DEFAULT_PROJECT_INTENT)
    spec["goal_summary"] = goal or spec.get("goal_summary", project_name)
    spec["project_name"] = project_name
    spec["project_intent"] = intent
    spec['http_contract'] = {
        'health_route': '/health',
        'generate_route': '/generate',
        'response_payloads': ['service_contract.json', 'sample_response.json', 'acceptance_report.json'],
    }
    return spec
