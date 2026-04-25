# Task - Project Queue Portfolio Mainline

## Queue Binding

- Queue Item: `ADHOC-20260425-project-queue-portfolio-mainline`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the repo can already push one rough-goal project through freeze/source/delivery, but the user now requires a serial multi-project queue path that produces per-project artifacts plus a portfolio summary without waiting for extra confirmations.
- Lane: Delivery Lane for the repo task itself, because this is a bounded runtime/project-generation implementation change inside the existing generation surface.
- Scope boundary: extend project-generation freeze/source artifact handling for queued rough-goal projects; do not rewrite support routing, benchmark infrastructure, or unrelated runtime wiring.

## Task Truth Source (single source for current task)

- task_purpose:
  - recognize multi-project queue requests and freeze a portfolio-oriented root output contract
  - process queued rough-goal projects serially into independent project directories with intake, freeze, design, build, verify, delivery, and summary artifacts
  - preserve existing single-project generation behavior and keep artifact/bundle contracts intact
  - emit a portfolio-level summary with bundle paths and dual-layer status fields
- routed_bug_class:
  - project-generation mainline upgrade for queued portfolio delivery
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260425-endurance-benchmark-formalization.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-endurance-benchmark-formalization.md`
  - `docs/41_low_capability_project_generation.md`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tests/test_project_generation_artifacts.py`
- forbidden_goal_shift:
  - do not regress single-project output_contract/source_generation behavior
  - do not weaken existing project-generation gates just to admit portfolio outputs
  - do not move project runs back into repo-owned runtime output locations
  - do not mix benchmark formalization, support bot routing, or unrelated cleanup into this task
- in_scope_modules:
  - project queue detection and freeze shaping
  - portfolio root artifact generation
  - serial per-project subrun orchestration
  - project/portfolio summary docs and bundles
  - targeted project-generation regressions
- out_of_scope_modules:
  - support/frontend dialogue logic
  - benchmark runner profiles and goldens
  - unrelated docs/contracts outside project-generation completion guidance
  - non-project-generation providers
- completion_evidence:
  - a queued project request can freeze as a portfolio root without breaking single-project contracts
  - source generation emits `portfolio_summary.json/.md` plus per-project directories with required artifacts, bundles, and status fields
  - targeted regression proves two queued rough goals are processed serially and final bundle/evidence paths are queryable

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260425-endurance-benchmark-formalization.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-endurance-benchmark-formalization.md`
  - `docs/41_low_capability_project_generation.md`
  - `AGENTS.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/42_frontend_backend_separation_contract.md`
  - `docs/50_prompt_hierarchy_contract.md`
  - `frontend/conversation_mode_router.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/classify_change_profile.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_bridge_views.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/module_protection_check.py`
  - `scripts/prompt_contract_check.py`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `scripts/workflow_checks.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_prompt_contract_check.py`
  - `tests/test_runtime_wiring_contract.py`
- Protected Paths:
  - support/frontend routing modules
  - benchmark runner and golden archives
  - any file outside the allowed write paths above
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `Project Queue Portfolio Mainline inherits the already-dirty lane-owned and frozen-kernel worktree from the prior protection-zone tasks so shared-worktree verify can remain auditable on 2026-04-25 while this task only changes project-generation runtime/docs/tests plus task/report bookkeeping`
- Forbidden Bypass:
  - no fake portfolio summary that omits per-project bundle/evidence/status paths
  - no generic README-only queue output in place of real per-project artifacts
  - no parallel multi-project mixing; queued projects must be processed serially
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python scripts/module_protection_check.py`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## Analysis / Find (before plan)

- Entrypoint analysis: `tools/providers/project_generation_artifacts.py` owns freeze/source/manifest/deliver normalization wrappers and is the narrowest place to branch queue mode while preserving the single-project path.
- Downstream consumer analysis: `scripts/project_generation_gate.py`, manifest readers, bundle builders, and benchmark summaries all rely on `output_contract_freeze.json`, `source_generation_report.json`, `project_manifest.json`, and `deliverable_index.json`.
- Source of truth:
  - `AGENTS.md`
  - `.agents/skills/ctcp-workflow/SKILL.md`
  - `.agents/skills/ctcp-gate-precheck/SKILL.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `docs/12_virtual_team_contract.md`
  - `docs/25_project_plan.md`
  - `docs/41_low_capability_project_generation.md`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tests/test_project_generation_artifacts.py`
- Current break point / missing wiring: the current project-generation path assumes one goal -> one project root; it does not preserve independent queued-project artifacts or portfolio verdict summaries.
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `normalize_output_contract_freeze()` and `normalize_source_generation_stage()` already provide a stable single-project contract that can be reused per queued subrun.
- current_module: queue detection, portfolio root shaping, and per-project artifact synthesis inside project-generation providers.
- downstream: manifest/deliverable index and benchmark consumers should still see one top-level runnable project while portfolio-specific consumers gain project-by-project evidence.
- source_of_truth: current project-generation contracts plus the Virtual Team lane artifact requirements.
- fallback: if a queued subproject cannot fully pass, emit its strongest deliverable bundle with explicit `first_failure_point`, remaining gaps, and `PARTIAL` or `NEEDS_REWORK` verdict inside the portfolio summary.
- acceptance_test:
  - `normalize_output_contract_freeze()` returns a stable root contract for queue requests
  - `normalize_source_generation()` processes queued projects serially and emits required per-project artifacts
  - `normalize_project_manifest()` and `normalize_deliverable_index()` still work for the top-level portfolio root
  - canonical repo checks remain green or the first failure is recorded precisely
- forbidden_bypass:
  - do not skip design/freeze artifacts and jump straight to project bundles
  - do not claim portfolio PASS when subproject user-acceptance coverage is insufficient
  - do not hide failures by collapsing all project outcomes into one top-level PASS
- user_visible_effect: queued rough-goal project batches become auditable deliverables instead of a single-project-only generation path.

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: Project generation can recognize a project queue request and freeze a portfolio-oriented root contract without regressing the existing single-project path.
- [ ] DoD-2: Source generation can process queued rough-goal projects serially into independent per-project directories with intake/freeze/design/build/verify/delivery artifacts, bundles, and status fields.
- [ ] DoD-3: A portfolio summary is emitted with project bundle paths, evidence bundle paths, internal_runtime_status, user_acceptance_status, first_failure_point, and final verdict for each queued project, and targeted regressions prove the path.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local readlist above)
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Rebind the task/report/archive bookkeeping for the portfolio-generation topic.
2. Add queue detection and portfolio-root freeze shaping in `project_generation_artifacts.py`.
3. Add serial queued-project orchestration and artifact synthesis in `project_generation_source_stage.py`.
4. Update the low-capability project-generation contract to acknowledge portfolio-root + per-project subrun output.
5. Add a regression that proves two rough-goal projects produce independent artifacts and one portfolio summary.
6. Run targeted tests, then repo gates, and record the first failure plus minimal repair if anything blocks.

## Notes / Decisions

- Default choices made: queue mode will keep one top-level runnable portfolio root and place independent project evidence under `portfolio_run/project_XX_<slug>/`.
- Alternatives considered: redefining the entire project-generation pipeline around multiple top-level run roots was rejected because it would break current manifest/deliverable gate assumptions.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - `None`
- Issue memory decision: no new issue-memory entry yet; treat this as a mainline capability extension unless a recurring user-visible regression appears during verify.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because this queued-portfolio path is still tightly local to the repo’s project-generation runtime and should stabilize behind tests before becoming a reusable skill.`
- persona_lab_impact: `none`

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260425-endurance-benchmark-formalization.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-endurance-benchmark-formalization.md`
  - `docs/41_low_capability_project_generation.md`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tests/test_project_generation_artifacts.py`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`: `PASS`
  - `python scripts/module_protection_check.py`: `PASS`
  - `python scripts/workflow_checks.py`: `PASS`
  - `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`: `PASS`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`: `PASS`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`: `PASS`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`: `FAIL` at `code health growth-guard`
- Queue status update suggestion (`todo/doing/done/blocked`): `blocked`

## Check / Contrast / Fix Loop Evidence

- check: targeted `test_project_generation_artifacts.py` now proves queue-mode freeze/source behavior without regressing existing single-project cases.
- contrast: after task-card repair, canonical verify still fails at `code health growth-guard` because `tools/providers/project_generation_artifacts.py`, `tools/providers/project_generation_source_stage.py`, and `tests/test_project_generation_artifacts.py` exceed the changed-file growth thresholds in the already-dirty shared worktree.
- fix: extract the new queue/portfolio logic and regression into smaller helper modules/files so the task-owned oversized files drop back under the growth-guard thresholds, then rerun canonical verify.

## Completion Criteria Evidence

- completion criteria evidence: must prove `connected + accumulated + consumed` for the queued portfolio path.
- connected: queue-mode freeze routes into a top-level runnable portfolio root and serial per-project subruns.
- accumulated: each queued project writes independent intake/freeze/design/build/verify/delivery artifacts plus bundle paths.
- consumed: portfolio summary enumerates those per-project outputs and the top-level manifest/deliver path can package the portfolio root.
