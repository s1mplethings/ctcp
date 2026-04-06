from __future__ import annotations

from .models import EndpointContract


def build_contract(spec: dict[str, object]) -> list[EndpointContract]:
    outputs = list(spec.get("required_outputs", []))
    return [
        EndpointContract("/health", "GET", "Return service health and archetype metadata", ["status", "archetype"]),
        EndpointContract("/generate", "POST", "Return spec/workflow/acceptance payload summary", outputs or ["spec", "workflow", "acceptance"]),
    ]
