from __future__ import annotations

import json
from typing import Any


def _manifest(output: dict[str, Any]) -> dict[str, Any]:
    candidate = output.get("agent_manifest")
    return candidate if isinstance(candidate, dict) else output


def _blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).lower().replace("-", "_")


def _tool_blob(manifest: dict[str, Any]) -> str:
    return _blob(manifest.get("tools", []))


def _workflow_blob(manifest: dict[str, Any]) -> str:
    return _blob(manifest.get("workflows", manifest.get("workflow", [])))


def _core_blob(manifest: dict[str, Any]) -> str:
    return _blob(
        {
            "agents": manifest.get("agents", []),
            "tools": manifest.get("tools", []),
            "workflows": manifest.get("workflows", manifest.get("workflow", [])),
            "memory": manifest.get("memory", []),
            "semantic_profile": manifest.get("semantic_profile", {}),
            "assumptions": manifest.get("assumptions", []),
            "clarification_needed": manifest.get("clarification_needed", []),
            "safe_defaults": manifest.get("safe_defaults", {}),
            "conflict_resolution": manifest.get("conflict_resolution", {}),
            "guardrails": manifest.get("guardrails", []),
        }
    )


def _capability_blob(manifest: dict[str, Any]) -> str:
    agents = []
    for agent in manifest.get("agents", []):
        if isinstance(agent, dict):
            agents.append({key: agent.get(key) for key in ("name", "role", "goal", "scope", "tools", "memory")})
    tools = []
    for tool in manifest.get("tools", []):
        if isinstance(tool, dict):
            tools.append({"tool_name": tool.get("tool_name"), "side_effect_level": tool.get("side_effect_level")})
    workflows = []
    for workflow in manifest.get("workflows", manifest.get("workflow", [])):
        if isinstance(workflow, dict):
            workflows.append({"state_name": workflow.get("state_name"), "tools_called": workflow.get("tools_called"), "responsible_agent": workflow.get("responsible_agent")})
    return _blob(
        {
            "agents": agents,
            "tools": tools,
            "workflows": workflows,
            "memory": manifest.get("memory", []),
            "semantic_profile": manifest.get("semantic_profile", {}),
            "conflict_resolution": manifest.get("conflict_resolution", {}),
        }
    )


def _workflow_state_blob(manifest: dict[str, Any]) -> str:
    return _blob([workflow.get("state_name") for workflow in manifest.get("workflows", manifest.get("workflow", [])) if isinstance(workflow, dict)])


DOMAIN_TERMS = {
    "devops": ["logs", "metrics", "deployment", "rollback", "incident", "postmortem"],
    "billing": ["billing", "charge", "refund"],
    "legal": ["legal", "lawyer", "liability", "contract", "clause"],
    "github": ["github", "pull_request", "merged_pr"],
    "github_pr": ["pull_request", "merged_pr", "merged prs"],
    "ecommerce": ["shopify", "orders", "product_page", "campaign"],
    "feedback": ["feedback", "classification", "trend", "weekly_report"],
    "refund": ["refund"],
    "rollback": ["rollback"],
    "contract": ["contract", "clause"],
    "legal_review": ["lawyer_review", "not_legal_advice", "risk"],
    "release_notes": ["release_notes", "breaking_change", "announcement_draft"],
    "customer_support": ["customer_support", "support_intake", "support.intake", "draft_response"],
    "customer_communication": ["customer_communication", "message.classify_risk", "risk_based_routing", "faq_auto_reply"],
}


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    del context
    manifest = _manifest(output)
    expectations = fixture.get("semantic_expectations", {})
    core = _core_blob(manifest)
    capability = _capability_blob(manifest)
    tools = _tool_blob(manifest)
    workflows = _workflow_blob(manifest)
    workflow_states = _workflow_state_blob(manifest)
    results: list[dict[str, str]] = []

    for keyword in expectations.get("required_keywords", []):
        token = str(keyword).lower().replace("-", "_")
        results.append(
            {
                "validator": "semantic_relevance",
                "assertion": f"required_keyword_{token}",
                "status": "pass" if token in core else "fail",
                "message": str(keyword),
            }
        )

    for keyword in expectations.get("forbidden_keywords", []):
        token = str(keyword).lower().replace("-", "_")
        results.append(
            {
                "validator": "semantic_relevance",
                "assertion": f"forbidden_keyword_{token}",
                "status": "fail" if token in capability else "pass",
                "message": str(keyword),
            }
        )

    for domain in expectations.get("required_tool_domains", []):
        terms = DOMAIN_TERMS.get(str(domain), [str(domain)])
        ok = any(term.lower().replace("-", "_") in tools for term in terms)
        results.append(
            {
                "validator": "semantic_relevance",
                "assertion": f"required_tool_domain_{domain}",
                "status": "pass" if ok else "fail",
                "message": str(domain),
            }
        )

    for domain in expectations.get("forbidden_tool_domains", []):
        terms = DOMAIN_TERMS.get(str(domain), [str(domain)])
        present = any(term.lower().replace("-", "_") in tools for term in terms)
        results.append(
            {
                "validator": "semantic_relevance",
                "assertion": f"forbidden_tool_domain_{domain}",
                "status": "fail" if present else "pass",
                "message": str(domain),
            }
        )

    for state in expectations.get("required_workflow_states", []):
        token = str(state).lower().replace("-", "_")
        results.append(
            {
                "validator": "semantic_relevance",
                "assertion": f"required_workflow_state_{token}",
                "status": "pass" if token in workflows else "fail",
                "message": str(state),
            }
        )

    for state in expectations.get("forbidden_workflow_states", []):
        token = str(state).lower().replace("-", "_")
        results.append(
            {
                "validator": "semantic_relevance",
                "assertion": f"forbidden_workflow_state_{token}",
                "status": "fail" if token in workflow_states else "pass",
                "message": str(state),
            }
        )
    return results
