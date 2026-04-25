# Task - lift Indie Studio Hub rough-goal freeze and user-acceptance coverage from team_task_pm_web to a composite production domain

## Queue Binding

- Queue Item: `ADHOC-20260423-indie-studio-hub-spec-freeze-domain-lift`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: support entry and task binding are already fixed; the first live breakpoint has moved to spec freeze collapsing Indie Studio Hub into `team_task_pm_web`.
- Lane: Virtual Team Lane, because this patch changes product-domain freeze logic, archetype materialization, and user-acceptance contracts for a rough-goal product request.
- Scope boundary: repair project-generation domain freeze, archetype materialization, and user-acceptance coverage gates for Indie Studio Hub style rough goals; do not touch support-entry routing/binding.

## Task Truth Source (single source for current task)

- task_purpose:
  - freeze indie-studio rough goals into an explicit composite product domain instead of `team_task_pm_web`
  - materialize a matching composite archetype with task, asset, bug, build/release, and docs/delivery surfaces
  - attach a stricter user-acceptance gate that requires the domain-specific pages, docs, and `10+` screenshots
  - preserve `internal_runtime_status` vs `user_acceptance_status` so internal PASS does not imply user PASS
- routed_bug_class:
  - rough-goal domain detection is currently overfitting on team-task signals
  - high-quality extended coverage still uses the team-task `8 pages / 8 screenshots` contract
  - user-level acceptance for the Indie Studio Hub ask is not expressed as a first-class status in delivery output
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
  - `contracts/project_domain_matrix.json`
  - `contracts/project_capability_bundles.json`
  - `tools/providers/project_generation_domain_contract.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/support_public_delivery.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_support_delivery_user_visible_contract.py`
  - external support session artifacts under `%TEMP%\ctcp_runs\ctcp\support_sessions\`
  - external bound run artifacts under `%TEMP%\ctcp_runs\ctcp\`
- forbidden_goal_shift:
  - do not edit support-entry routing or task-binding code
  - do not widen this turn into unrelated cleanup of the dirty worktree
  - do not weaken the existing Plane-lite benchmark contract while adding the new domain
- in_scope_modules:
  - project-domain matrix and capability contract
  - project-generation decision/freeze logic
  - generated archetype files and extended coverage materialization
  - user-visible delivery/user-acceptance status reporting
  - focused regressions and one real support-bot rerun
- out_of_scope_modules:
  - support entry classification and run binding
  - unrelated frozen-kernel worktree cleanup
  - non-project-generation features outside the Indie Studio Hub domain lift
- completion_evidence:
  - a fresh support-bot rerun binds a real run, selects `wf_project_generation_manifest`, and freezes to a new composite domain/archetype
  - generated output contains Asset / Bug / Build-Release / Docs Center coverage plus the four missing docs and `10+` screenshots
  - delivery output exposes `internal_runtime_status` and `user_acceptance_status`, and user acceptance only passes when the stricter domain gate passes

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
  - `contracts/project_domain_matrix.json`
  - `contracts/project_capability_bundles.json`
  - `tools/providers/project_generation_domain_contract.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/support_public_delivery.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_support_delivery_user_visible_contract.py`
  - external support session artifacts under `%TEMP%\ctcp_runs\ctcp\support_sessions\`
  - external bound run artifacts under `%TEMP%\ctcp_runs\ctcp\`
- Protected Paths:
  - support-entry routing/binding implementation paths not listed above
  - unrelated frozen-kernel files
  - unrelated dirty files outside this patch scope
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `N/A`
- Forbidden Bypass:
  - no direct run creation before using the support bot for rerun validation
  - no fabricated PASS verdict without real run artifacts
  - no changing Plane-lite expectations to “pass” the Indie Studio Hub case
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python -m unittest discover -s tests -p "test_plane_lite_benchmark_regression.py" -v`
  - `python -m unittest discover -s tests -p "test_support_delivery_user_visible_contract.py" -v`
  - `python scripts/ctcp_support_bot.py --stdin --chat-id <fixed_id>`
  - artifact inspection for support session state/reply, `find_result.json`, `output_contract_freeze.json`, generated docs, screenshots, and `support_public_delivery.json`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`

## Analysis / Find

- Source of truth:
  - `AGENTS.md`
  - `meta/tasks/CURRENT.md`
  - `contracts/project_domain_matrix.json`
  - `contracts/project_capability_bundles.json`
  - `tools/providers/project_generation_domain_contract.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/support_public_delivery.py`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
- Current break point / missing wiring:
  - the domain matrix and freeze logic still route Indie Studio Hub rough goals into the team-task family, and the extended coverage ledger still enforces only the team-task contract.
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: user requires the first live breakpoint to move from spec freeze failure to a real composite Indie Studio Hub freeze.
- current_module: project-generation domain routing, archetype generation, extended coverage gating, and delivery status reporting.
- downstream: output contract freeze, project manifest, delivery manifest, screenshot/doc generation, and user-facing rerun verdict.
- source_of_truth: real generated run artifacts under `%TEMP%\ctcp_runs`.
- fallback: if rerun still lands on the wrong domain or under-generates the required docs/views, record the first remaining failure point and stop there.
- acceptance_test:
  - focused artifact/unit regressions
  - one real support-bot rerun with the same rough-goal style input
  - artifact inspection of freeze/domain/docs/screenshots/status fields
  - workflow checks and canonical verify record
- forbidden_bypass:
  - no support-entry code changes
  - no claiming user PASS from internal PASS alone
- user_visible_effect: Indie Studio rough goals should now freeze and generate as a composite production hub, and delivery should explicitly separate internal runtime pass from user acceptance.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Indie-studio rough goals freeze to an explicit composite domain/archetype instead of `team_task_pm_web`, and the frozen spec includes tasks, assets, bugs, build-release, and docs-delivery.
- [x] DoD-2: User-acceptance coverage for that domain hard-requires Asset Library, Asset Detail, Bug Tracker, Build / Release Center, Docs Center, milestone/startup/replay/mid-stage docs, and `10+` screenshots.
- [x] DoD-3: A fresh rough-goal rerun proves the new freeze path, reports `internal_runtime_status` plus `user_acceptance_status`, and no longer lands on `team_task_pm_web`.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A - repo-local contracts and prior rerun evidence are sufficient`
- [x] Code changes allowed
- [x] Focused code/tests landed
- [x] Real dialogue rerun executed
- [x] Final CTCP output captured
- [x] Support/bound-run artifact inspection completed
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Archive the completed rerun-review task and bind this spec-freeze/domain-lift repair task.
2. Add a composite Indie Studio Hub domain plus capability family and route the rough-goal signals there.
3. Materialize a matching generated archetype and extended coverage ledger for assets, bugs, builds/releases, docs, and `10+` screenshots.
4. Expose explicit `internal_runtime_status` and `user_acceptance_status` in delivery output.
5. Run focused regressions, then re-run the rough goal through the repaired support bot path and audit the generated artifacts.

## Notes / Decisions

- Default environment choice: `%TEMP%\ctcp_runs` because `D:\ctcp_runs` is not writable in this environment.
- Skill decision (`skillized: yes`): use `ctcp-workflow` for the bind -> spec/domain repair -> verify -> report loop.
- Issue memory decision: promote the defect class to `indie_studio_rough_goal_domain_collapse`.
- persona_lab_impact: none.

## Check / Contrast / Fix Loop Evidence

- check: the latest real rerun proved entry/binding are healthy, but `output_contract_freeze.json` still resolved to `team_task_management/team_task_pm/team_task_pm_web`.
- contrast: the intended result is an explicit Indie Studio composite domain with first-class asset, bug, build/release, docs, and `10+` screenshot coverage.
- fix: this patch will change the project-generation domain matrix, freeze/archetype decisions, generated business scaffold, extended coverage ledger, and delivery status reporting to match that composite domain.

## Completion Criteria Evidence

- completion criteria evidence: must prove `connected + accumulated + consumed` for rough-goal signal -> new domain freeze -> generated composite scaffold -> user-acceptance gate -> explicit dual verdict.
- connected: fresh rerun must bind through support bot and freeze to the new domain/archetype.
- accumulated: generated project output must contain the required composite modules, docs, screenshots, and delivery artifacts.
- consumed: final verdict must use `internal_runtime_status` separately from `user_acceptance_status`.

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-rerun-test.md`
  - `contracts/project_domain_matrix.json`
  - `contracts/project_capability_bundles.json`
  - `tools/providers/project_generation_domain_contract.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/support_public_delivery.py`
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_support_delivery_user_visible_contract.py`
- Verification summary: `focused regressions passed, workflow_checks passed, real support-bot rerun passed, verify_repo doc-only failed only on unrelated shared-worktree module-protection noise`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
