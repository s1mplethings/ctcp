from __future__ import annotations

from typing import Any


def enrich_generic_goal_spec(
    spec: dict[str, Any],
    *,
    goal: str,
    project_archetype: str,
    delivery_shape: str,
    web_shape: str,
) -> None:
    goal_text = str(goal or "").strip()
    if project_archetype == "web_service" or delivery_shape == web_shape:
        notes = [
            "local web service reachable from a browser on the same machine or LAN when requested by the goal",
            "standard-library HTTP route surface with a deterministic startup/self-test path",
        ]
        spec["goal_specific_scope"] = [goal_text, *notes] if goal_text else notes
        spec["acceptance_criteria"] = [
            "README startup command exits or self-tests successfully",
            "local web entrypoint exposes `/` and `/status` when the project is web/mobile oriented",
            "the generated tests exercise the same service methods and model constructors used by the entrypoint",
            "sample data matches the concrete user-goal flow instead of generic placeholder records",
        ]
    elif goal_text:
        spec["goal_specific_scope"] = [goal_text]


def enrich_output_project_spec(
    goal: str,
    base_spec: dict[str, Any],
    project_intent: dict[str, Any],
    project_domain: str,
    scaffold_family: str,
    project_type: str,
    project_archetype: str,
    delivery_shape: str,
) -> dict[str, Any]:
    from tools.providers.project_generation_decisions import WEB_SHAPE, enrich_project_spec

    spec = enrich_project_spec(
        goal=goal,
        base_spec=base_spec,
        project_intent=project_intent,
        project_domain=project_domain,
        scaffold_family=scaffold_family,
        project_type=project_type,
        project_archetype=project_archetype,
        delivery_shape=delivery_shape,
    )
    if project_domain == "generic_software_project":
        enrich_generic_goal_spec(
            spec,
            goal=goal,
            project_archetype=project_archetype,
            delivery_shape=delivery_shape,
            web_shape=WEB_SHAPE,
        )
    return spec
