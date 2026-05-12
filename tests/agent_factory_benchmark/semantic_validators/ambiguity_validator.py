from __future__ import annotations

from typing import Any


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    del context
    if not fixture.get("semantic_expectations", {}).get("ambiguity_case"):
        return []
    manifest = _manifest(output)
    checks = {
        "assumptions": manifest.get("assumptions"),
        "clarification_needed": manifest.get("clarification_needed"),
        "safe_defaults": manifest.get("safe_defaults"),
        "minimal_viable_agent": manifest.get("minimal_viable_agent"),
    }
    results: list[dict[str, str]] = []
    for key, value in checks.items():
        if isinstance(value, list):
            ok = bool(value)
        elif isinstance(value, dict):
            ok = bool(value)
        else:
            ok = bool(value)
        results.append(
            {
                "validator": "semantic_ambiguity",
                "assertion": f"ambiguity_has_{key}",
                "status": "pass" if ok else "fail",
                "message": key,
            }
        )
    return results
