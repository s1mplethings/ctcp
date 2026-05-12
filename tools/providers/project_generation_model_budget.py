from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TIERS: dict[str, dict[str, Any]] = {
    "tier_3_strong": {
        "use_for": ["intent_director", "complex_architecture", "final_hard_repair"],
        "max_calls_per_run": 3,
    },
    "tier_2_medium": {
        "use_for": ["product_spec", "library_plan", "architecture_plan", "file_manifest", "escalated_file_author"],
        "max_calls_per_run": 8,
    },
    "tier_1_cheap": {
        "use_for": ["file_author", "test_author", "simple_repair"],
        "max_calls_per_run": 50,
    },
    "tier_0_local": {
        "use_for": ["skeleton", "validation", "formatting", "packaging", "librarian_retrieval"],
        "max_calls_per_run": 0,
    },
}

ESCALATION_RULES: list[dict[str, str]] = [
    {"when": "same_file_failed_twice", "from": "tier_1_cheap", "to": "tier_2_medium"},
    {"when": "architecture_contract_conflict", "from": "tier_2_medium", "to": "tier_3_strong"},
]

DEFAULT_STAGE_TIERS: dict[str, str] = {
    "intent_director": "tier_3_strong",
    "product_spec": "tier_2_medium",
    "library_plan": "tier_2_medium",
    "architecture_plan": "tier_2_medium",
    "file_manifest": "tier_2_medium",
    "file_author": "tier_1_cheap",
    "test_author": "tier_1_cheap",
    "simple_repair": "tier_1_cheap",
    "validation": "tier_0_local",
    "skeleton": "tier_0_local",
    "librarian_retrieval": "tier_0_local",
}


def choose_model_tier(
    *,
    stage: str,
    file_task: dict[str, Any] | None = None,
    failure_count: int = 0,
    architecture_contract_conflict: bool = False,
) -> dict[str, Any]:
    stage_name = str(stage or "").strip() or "unknown"
    tier = DEFAULT_STAGE_TIERS.get(stage_name, "tier_1_cheap")
    reason = "default stage policy"
    escalated = False
    if architecture_contract_conflict and tier == "tier_2_medium":
        tier = "tier_3_strong"
        reason = "architecture_contract_conflict"
        escalated = True
    elif stage_name in {"file_author", "simple_repair"} and failure_count >= 2:
        tier = "tier_2_medium"
        reason = "same_file_failed_twice"
        escalated = True
    row: dict[str, Any] = {
        "stage": stage_name,
        "tier": tier,
        "reason": reason,
        "attempt": max(1, int(failure_count) + 1),
        "escalated": escalated,
    }
    if isinstance(file_task, dict) and str(file_task.get("path", "")).strip():
        row["path"] = str(file_task["path"]).strip().replace("\\", "/")
        row["implementation_mode"] = str(file_task.get("implementation_mode", "")).strip()
        row["primary_libraries"] = [str(item) for item in file_task.get("primary_libraries", []) if str(item)]
    return row


def build_model_budget(
    *,
    file_tasks: list[dict[str, Any]] | None = None,
    extra_stage_choices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    choices = [
        choose_model_tier(stage="intent_director"),
        choose_model_tier(stage="product_spec"),
        choose_model_tier(stage="library_plan"),
        choose_model_tier(stage="architecture_plan"),
        choose_model_tier(stage="file_manifest"),
        choose_model_tier(stage="librarian_retrieval"),
        choose_model_tier(stage="skeleton"),
        choose_model_tier(stage="validation"),
    ]
    for task in file_tasks or []:
        if isinstance(task, dict):
            choices.append(choose_model_tier(stage="file_author", file_task=task))
    for row in extra_stage_choices or []:
        if isinstance(row, dict):
            choices.append(dict(row))
    return {
        "schema_version": "ctcp-model-budget-v1",
        "policy": "strong_models_reduce_uncertainty; cheap_models_author_bounded_files; local_code_validates",
        "tiers": TIERS,
        "stage_choices": choices,
        "escalation_rules": ESCALATION_RULES,
        "call_limits": {name: int(row.get("max_calls_per_run", 0)) for name, row in TIERS.items()},
    }


def write_model_budget_artifact(
    *,
    run_dir: Path,
    file_tasks: list[dict[str, Any]] | None = None,
    extra_stage_choices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    budget = build_model_budget(file_tasks=file_tasks, extra_stage_choices=extra_stage_choices)
    rel = "artifacts/model_budget.json"
    path = run_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(budget, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    budget["path"] = rel
    return budget


__all__ = ["build_model_budget", "choose_model_tier", "write_model_budget_artifact"]
