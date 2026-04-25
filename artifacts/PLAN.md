# Root Plan Artifact

Status: SIGNED
Scope-Allow: AGENTS.md, agent_league_cases, agents, analyze_test_results.py, artifacts, contracts, ctcp_adapters, ctcp_backend_interface_patch_81f8f35.zip, ctcp_pointcloud_concrete_impl_taskpack, ctcp_pointcloud_full_project_taskpack, ctcp_v2p_fixture_clean_taskpack, docs, frontend, generated_projects, llm_core, meta, plane_lite_team_pm_test_pack.zip, scripts, templates, test_final.py, test_support_flow.py, test_support_flow_fixed.py, test_support_flow_simple.py, tests, tools, workflow_registry
Scope-Deny: src, include, web, CMakeLists.txt
Gates: lite, workflow_gate, prompt_contract_check, plan_check, patch_check, behavior_catalog_check
Budgets: max_iterations=12, max_files=550, max_total_bytes=5000000
Stop: prompt_hierarchy=root_authority_locked, frozen_kernel_gate=elevation_enforced, canonical_verify=run_to_stable_conclusion
Behaviors: B002, B003, B004, B005, B006, B007, B010, B011, B034
Results: R201, R202, R203, R204

## Goal

This root plan artifact exists to define the active repository scope for the `plan-scope-budget-hygiene` task and to keep canonical CTCP verify honest while the shared worktree still contains a large mixed dirty set from the current mainline plus retained historical deletions.

The goal of this run is not to introduce new product behavior. The goal is to make `artifacts/PLAN.md` truthful to the current dirty worktree so `patch_check` reports the next real blocker instead of failing on stale file-budget or stale scope assumptions.

## Current Worktree Focus

The relevant work in the current worktree includes:

- the current CTCP governance, prompt-contract, workflow, and verify changes already present across `AGENTS.md`, `agents/`, `docs/`, `scripts/`, `tests/`, and `tools/`
- the support-routing, run-manifest, benchmark, Agent League, and project-generation/domain-lift mainline changes already present under `frontend/`, `contracts/`, `workflow_registry/`, `agent_league_cases/`, and supporting runtime code
- meta task/report/archive updates that make the recent benchmark, dialogue-routing, domain-lift, shared-worktree, protection-zone, and current PLAN-budget tasks auditable
- historical deleted artifacts, generated-project outputs, taskpacks, and standalone helper/test files that are still part of the shared dirty worktree and therefore still counted by `patch_check`

## Why Scope-Allow Is Broad

`patch_check` evaluates the entire current dirty worktree, not only the files touched in the newest task. The current dirty set spans both active mainline roots and older historical deletions. For that reason, `Scope-Allow` intentionally covers the real dirty roots still present today:

- `AGENTS.md`
- `agent_league_cases/`
- `agents/`
- `analyze_test_results.py`
- `artifacts/`
- `contracts/`
- `ctcp_adapters/`
- `ctcp_backend_interface_patch_81f8f35.zip`
- `ctcp_pointcloud_concrete_impl_taskpack/`
- `ctcp_pointcloud_full_project_taskpack/`
- `ctcp_v2p_fixture_clean_taskpack/`
- `docs/`
- `frontend/`
- `generated_projects/`
- `llm_core/`
- `meta/`
- `plane_lite_team_pm_test_pack.zip`
- `scripts/`
- `templates/`
- `test_final.py`
- `test_support_flow.py`
- `test_support_flow_fixed.py`
- `test_support_flow_simple.py`
- `tests/`
- `tools/`
- `workflow_registry/`

This keeps the plan truthful to the real repository state and prevents `patch_check` from failing on stale scope definitions before it can expose the next actual issue.

## Human Summary

Expected progression for this step:

1. classify the real dirty worktree into keep, revert, archive, and manual-review buckets so the scope/budget discussion is evidence-based.
2. prefer the smallest safe reconciliation path; if shrinking the dirty set is not provably safe, update the root PLAN to match the real current dirty roots and file-count budget.
3. rerun `module_protection_check`, `workflow_checks`, and canonical `doc-only` verify so `patch_check` either passes or exposes the next exact blocker.
4. record the resulting first remaining failure point, or full PASS, in `meta/reports/LAST.md`.
