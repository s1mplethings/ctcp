from __future__ import annotations

import json
from typing import Any


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def _blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).lower().replace("-", "_").replace(" ", "_")


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    del context
    if not fixture.get("semantic_expectations", {}).get("conflict_case"):
        return []
    manifest = _manifest(output)
    blob = _blob(
        {
            "conflict_resolution": manifest.get("conflict_resolution", {}),
            "workflows": manifest.get("workflows", manifest.get("workflow", [])),
            "permissions": manifest.get("permissions", {}),
            "guardrails": manifest.get("guardrails", []),
        }
    )
    required = {
        "risk_based_routing": "risk_based_routing",
        "legal_approval": "legal_approval",
        "account_manager_approval": "account_manager_approval",
        "auto_reply_only_for_low_risk_faq": "auto_reply_only_for_low_risk_faq",
    }
    return [
        {
            "validator": "semantic_conflict_resolution",
            "assertion": assertion,
            "status": "pass" if token in blob else "fail",
            "message": token,
        }
        for assertion, token in required.items()
    ]
