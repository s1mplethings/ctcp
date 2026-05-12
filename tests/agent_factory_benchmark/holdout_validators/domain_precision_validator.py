from __future__ import annotations

from typing import Any

from tests.agent_factory_benchmark.holdout_validators.common import capability_blob, result, tool_names, workflow_names


DOMAIN_TERMS = {
    "devops": {"logs", "metrics", "deployment", "production.rollback", "postmortem"},
    "billing": {"billing", "refund", "payment", "charge.lookup"},
    "payment": {"payment", "billing.charge", "refund"},
    "refund": {"refund"},
    "legal": {"legal", "lawyer", "external_legal"},
    "github_issue": {"github.issue", "issue.close", "issue.mark"},
    "incident": {"incident_response", "incident_timeline", "postmortem"},
    "rollback": {"rollback"},
}


def _contains_domain(doc: dict[str, Any], domain: str) -> bool:
    terms = DOMAIN_TERMS.get(domain, {domain})
    blob = capability_blob(doc)
    return any(term in blob for term in terms)


def validate(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    del context
    expectations = fixture.get("holdout_expectations", {})
    results: list[dict[str, str]] = []
    for domain in expectations.get("forbidden_domains", []):
        results.append(
            result(
                "holdout_domain_precision",
                f"forbidden_domain_{domain}",
                not _contains_domain(output, str(domain)),
                str(domain),
            )
        )

    if expectations.get("non_billing_charge"):
        names = tool_names(output)
        billing_hits = sorted(name for name in names if any(term in name for term in ("billing", "refund", "payment")))
        results.append(
            result(
                "holdout_domain_precision",
                "charge_not_payment_or_refund",
                not billing_hits,
                ", ".join(billing_hits) or "no billing/payment/refund tools",
            )
        )

    states = workflow_names(output)
    for state in expectations.get("required_workflow_states", []):
        token = str(state).lower()
        results.append(
            result(
                "holdout_domain_precision",
                f"required_workflow_state_{token}",
                token in states,
                token,
            )
        )
    return results
