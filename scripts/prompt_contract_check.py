#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    pattern: str
    kind: str = "required"


@dataclass(frozen=True)
class FileSpec:
    path: str
    rules: tuple[Rule, ...]


SPECS: tuple[FileSpec, ...] = (
    FileSpec(
        path="AGENTS.md",
        rules=(
            Rule("agents_delivery_lane", "formal Delivery Lane heading", r"(?im)^###\s*Delivery Lane\b"),
            Rule("agents_virtual_team_lane", "formal Virtual Team Lane heading", r"(?im)^###\s*Virtual Team Lane\b"),
            Rule(
                "agents_virtual_team_gate",
                "Virtual Team implementation gate",
                r"(?i)Implementation entry gate for Virtual Team Lane",
            ),
            Rule(
                "agents_not_optional_style",
                "Virtual Team Lane not treated as optional styling",
                r"(?i)Do not treat Virtual Team Lane as optional styling",
            ),
        ),
    ),
    FileSpec(
        path="docs/12_virtual_team_contract.md",
        rules=(
            Rule("vt_contract_triggers", "trigger conditions section", r"(?im)^##\s*2\)\s*Trigger Conditions\b"),
            Rule("vt_contract_roles", "team roles and boundaries section", r"(?im)^##\s*3\)\s*Team Roles and Boundaries\b"),
            Rule("vt_contract_product_lead", "Product Lead role boundary", r"(?im)^###\s*3\.1\s*Product Lead\b"),
            Rule("vt_contract_artifacts", "mandatory team-design artifacts", r"(?im)^##\s*4\)\s*Mandatory Team-Design Artifacts\b"),
            Rule("vt_contract_gate", "design-to-implementation gate", r"(?im)^##\s*5\)\s*Design-to-Implementation Gate\b"),
            Rule("vt_contract_shortcuts", "forbidden shortcuts", r"(?im)^##\s*6\)\s*Forbidden Shortcuts\b"),
            Rule("vt_contract_completion", "completion standard", r"(?im)^##\s*8\)\s*Completion Standard\b"),
        ),
    ),
    FileSpec(
        path="docs/10_team_mode.md",
        rules=(
            Rule(
                "team_mode_prompt_not_unique_entry",
                "PROMPT.md is not described as a unique entry/authority",
                r"(?i)PROMPT\.md.*(唯一入口|唯一输入|independent authority|unique entry)",
                kind="forbidden",
            ),
            Rule(
                "team_mode_bridge_truth_only",
                "customer-facing truth stays on bridge/backend snapshot interfaces",
                r"(?i)get_support_context.*get_current_state_snapshot.*get_render_state_snapshot|不得在客服层直接扫描 `RUN\.json` / `verify_report\.json` / `TRACE\.md`",
            ),
        ),
    ),
    FileSpec(
        path="agents/prompts/chair_plan_draft.md",
        rules=(
            Rule(
                "chair_not_patch_first",
                "legacy patch-first phrase removed",
                r"(?i)You are a patch-first coding agent\.",
                kind="forbidden",
            ),
            Rule("chair_lane_judgment", "lane judgment", r"(?i)lane judgment|Lane:\s*DELIVERY\|VIRTUAL_TEAM"),
            Rule("chair_product_direction", "product direction", r"(?im)^###\s*Product Direction\b"),
            Rule("chair_architecture_direction", "architecture direction", r"(?im)^###\s*Architecture Direction\b"),
            Rule("chair_ux_flow", "UX flow", r"(?im)^###\s*UX Flow\b"),
            Rule("chair_role_handoff", "role handoff", r"(?im)^###\s*Role Handoff\b"),
            Rule("chair_acceptance_matrix", "acceptance matrix", r"(?im)^###\s*Acceptance Matrix\b"),
            Rule("chair_stop_conditions", "stop conditions", r"(?im)^-\s*Stop:\s*"),
        ),
    ),
    FileSpec(
        path="docs/50_prompt_hierarchy_contract.md",
        rules=(
            Rule("prompt_hierarchy_root", "AGENTS.md is root authority", r"(?i)AGENTS\.md.*root contract"),
            Rule("prompt_hierarchy_task_layer", "CURRENT.md participates in source order", r"(?i)meta/tasks/CURRENT\.md"),
            Rule("prompt_hierarchy_compiled_prompt", "PROMPT.md is compiled/derived", r"(?i)PROMPT\.md.*compiled|compiled/derived artifact"),
            Rule(
                "prompt_hierarchy_no_override",
                "compiled prompt cannot override root contract",
                r"(?i)must not .*override.*root contract|must not introduce new top-level rules",
            ),
        ),
    ),
    FileSpec(
        path="docs/04_execution_flow.md",
        rules=(
            Rule("flow_lane_split", "formal work-lane split", r"(?i)Formal work-lane split"),
            Rule(
                "flow_lane_recorded",
                "lane must be recorded before implementation",
                r"(?i)lane selection must be recorded before implementation work starts",
            ),
            Rule(
                "flow_design_gate",
                "Virtual Team design gate before implementation",
                r"(?i)required design artifacts must exist before implementation",
            ),
            Rule("flow_virtual_team_path", "Virtual Team path subflow", r"(?i)Project Generation Fixed Subflow \(Virtual Team Path\)"),
            Rule(
                "flow_design_before_implementation",
                "product/interaction/technical complete before implementation",
                r"(?i)product_brief.*interaction_design.*technical_plan|must all complete before `implementation`",
            ),
        ),
    ),
    FileSpec(
        path="docs/11_task_progress_dialogue.md",
        rules=(
            Rule("dialogue_current_lane", "current_lane binding", r"(?i)`current_lane`"),
            Rule("dialogue_active_role", "active_role binding", r"(?i)`active_role`"),
            Rule("dialogue_updated_artifacts", "updated_artifacts binding", r"(?i)`updated_artifacts`"),
            Rule("dialogue_pending_decisions", "pending_decisions binding", r"(?i)`pending_decisions`"),
            Rule("dialogue_virtual_team_progress", "Virtual Team Lane progress section", r"(?i)Virtual Team Lane Progress"),
        ),
    ),
    FileSpec(
        path="docs/14_persona_test_lab.md",
        rules=(
            Rule(
                "persona_authority_to_docs12",
                "authority points to docs/12_virtual_team_contract.md",
                r"(?i)docs/12_virtual_team_contract\.md",
            ),
            Rule(
                "persona_allows_vt_role_model",
                "production may legitimately use Virtual Team Lane role model",
                r"(?i)may legitimately use a Virtual Team Lane role model in production",
            ),
            Rule(
                "persona_old_conflict_removed",
                "old conflicting hierarchy sentence removed",
                r"(?i)not a parallel role hierarchy that changes CTCP mainline flow",
                kind="forbidden",
            ),
        ),
    ),
)


def run_checks(root: Path) -> tuple[int, list[str]]:
    passed = 0
    failed = 0
    lines: list[str] = []

    for spec in SPECS:
        path = root / spec.path
        if not path.exists():
            failed += 1
            lines.append(f"[prompt_contract_check] FAIL {spec.path} :: file_missing :: required file not found")
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        for rule in spec.rules:
            matched = bool(re.search(rule.pattern, text))
            if rule.kind == "required":
                if matched:
                    passed += 1
                    lines.append(f"[prompt_contract_check] PASS {spec.path} :: {rule.rule_id} :: {rule.description}")
                else:
                    failed += 1
                    lines.append(
                        f"[prompt_contract_check] FAIL {spec.path} :: {rule.rule_id} :: missing required marker for {rule.description}"
                    )
            elif rule.kind == "forbidden":
                if matched:
                    failed += 1
                    lines.append(
                        f"[prompt_contract_check] FAIL {spec.path} :: {rule.rule_id} :: forbidden marker present for {rule.description}"
                    )
                else:
                    passed += 1
                    lines.append(f"[prompt_contract_check] PASS {spec.path} :: {rule.rule_id} :: {rule.description}")
            else:
                raise ValueError(f"unknown rule kind: {rule.kind}")

    total = passed + failed
    lines.append(f"[prompt_contract_check] SUMMARY total={total} passed={passed} failed={failed}")
    lines.append("[prompt_contract_check] ok" if failed == 0 else "[prompt_contract_check] error")
    return (0 if failed == 0 else 1), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Virtual Team Lane prompt/contract landing")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to validate")
    args = parser.parse_args(argv)

    rc, lines = run_checks(args.root.resolve())
    for line in lines:
        print(line)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
