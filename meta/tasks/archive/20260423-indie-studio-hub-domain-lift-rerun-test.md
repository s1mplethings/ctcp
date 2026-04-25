# Task - re-run Indie Studio Hub Domain Lift rough-goal generation test through repaired support entry

## Queue Binding

- Queue Item: `ADHOC-20260423-indie-studio-hub-domain-lift-rerun-test`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user wants a fresh coarse-goal Domain Lift generation test now that the support entry and binding path have been repaired.
- Lane: Virtual Team Lane validation, because the run under test must freeze a rough product goal into a multi-domain project-generation plan before implementation.
- Scope boundary: initiate the task only through the real support bot path, inspect the resulting run/spec/delivery artifacts, and report the product-domain verdict; do not change support-entry routing code or product-generation implementation in this turn.

## Task Truth Source (single source for current task)

- task_purpose:
  - submit the Indie Studio Hub Domain Lift request through the repaired support bot entry using a rough-goal prompt only
  - verify that the support session binds a real run with non-empty `active_goal`, `bound_run_id`, and `bound_run_dir`
  - verify that the bound run selects `wf_project_generation_manifest`
  - inspect spec-freeze and delivery artifacts for product-domain breadth, missing documents, screenshot count, and the split between `internal_runtime_status` and `user_acceptance_status`
- routed_validation_focus:
  - whether the repaired entry stays on the project-generation mainline for a fresh session
  - whether the generated product still collapses to `team_task_pm_web`
  - whether the run produces first-class asset, bug, build/release, and docs-center coverage rather than only task-management coverage
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
  - external support session artifacts under `%TEMP%\ctcp_runs\ctcp\support_sessions\`
  - external bound run artifacts under `%TEMP%\ctcp_runs\ctcp\`
- forbidden_goal_shift:
  - do not edit support-entry routing/binding code in this turn
  - do not expand or repair the Indie Studio Hub product implementation itself
  - do not bypass the support bot by calling project-generation entrypoints directly for initiation
- in_scope_modules:
  - support-bot stdin conversation path for one fresh session
  - bound support session state and reply artifacts
  - bound run artifacts under the selected project-generation workflow
  - generated project/docs/screenshot outputs under the external run
- out_of_scope_modules:
  - support-entry routing/binding implementation
  - Domain Lift business/product repair implementation
  - unrelated cleanup of the dirty repo worktree
  - any attempt to convert this test into a new fix task inside the same patch
- completion_evidence:
  - a fresh support session artifact shows non-empty `active_goal`, `bound_run_id`, and `bound_run_dir`
  - the bound run artifact shows `selected_workflow_id = wf_project_generation_manifest`
  - artifact review explicitly reports product-domain freeze result, docs/screenshot coverage, `internal_runtime_status`, `user_acceptance_status`, and first failure point
  - `meta/reports/LAST.md` records the real command evidence and final rerun verdict

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
  - external support session artifacts under `%TEMP%\ctcp_runs\ctcp\support_sessions\`
  - external bound run artifacts under `%TEMP%\ctcp_runs\ctcp\`
- Protected Paths:
  - support-entry routing/binding implementation files
  - repo implementation files for Indie Studio Hub product-domain expansion itself
  - frozen-kernel files
  - unrelated dirty files outside this dialogue-test scope
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `N/A`
- Forbidden Bypass:
  - no support-entry code changes
  - no direct orchestrator/project-generation start before support-bot initiation
  - no fabricated validation result or inferred coverage without a real artifact
- Acceptance Checks:
  - `python scripts/ctcp_support_bot.py --stdin --chat-id <fixed_id>`
  - artifact inspection for `artifacts/support_reply.json`, `artifacts/support_session_state.json`, `artifacts/find_result.json`, spec-freeze artifacts, docs outputs, and screenshots
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`

## Analysis / Find

- Source of truth:
  - `AGENTS.md`
  - `meta/tasks/CURRENT.md`
  - `scripts/project_generation_gate.py`
  - `docs/12_virtual_team_contract.md`
  - `docs/30_artifact_contracts.md`
  - `docs/41_low_capability_project_generation.md`
  - prior generation-test evidence in `meta/reports/archive/20260423-indie-studio-hub-generation-test.md`
  - prior routing-fix evidence in `meta/reports/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
- Current break point under test:
  - whether the repaired support entry can now carry a fresh rough-goal Domain Lift request into a real project-generation run that materially expands beyond `team_task_pm_web`.
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: user requires a real rerun through the repaired support bot path, with verdict based on actual run evidence.
- current_module: support session creation plus project-generation run inspection.
- downstream: support reply/state, workflow selection, spec freeze, generated project outputs, docs, screenshots, and acceptance verdict.
- source_of_truth: actual support session and run artifacts under `%TEMP%\ctcp_runs`.
- fallback: if the run does not bind or does not finish, record the first real blocker/failure point and stop there rather than turning this into a fix task.
- acceptance_test:
  - support stdin dialogue with one fixed chat id
  - support session and bound-run artifact inspection
  - project output/docs/screenshot artifact inspection
  - workflow checks and repo verify record
- forbidden_bypass:
  - no direct run creation outside support bot
  - no claiming PASS if route, spec freeze, or delivery coverage still fails
- user_visible_effect: this request should now produce a real project-generation run and a grounded product-domain verdict from the generated artifacts.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: A real support-bot dialogue binds a fresh run for the Indie Studio Hub Domain Lift rough-goal request and the selected workflow is `wf_project_generation_manifest`.
- [x] DoD-2: Artifact review records whether the spec freeze still collapses to `team_task_pm_web` or expands to the expected asset, bug, build-release, and docs center domains.
- [x] DoD-3: The final report records `internal_runtime_status`, `user_acceptance_status`, screenshot/doc coverage, first failure point, and `PASS/PARTIAL/NEEDS_REWORK` verdict from real run evidence.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A - repo-local support entrypoint and prior run evidence sufficient`
- [x] Code changes allowed (`meta/*` only for task/report rebinding in this turn)
- [x] Real dialogue rerun executed
- [x] Final CTCP output captured
- [x] Support/bound-run artifact inspection completed
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Archive the completed routing/binding repair task and bind this rerun-validation task.
2. Start one fresh support-bot stdin session with the rough-goal Domain Lift request.
3. Inspect the support session artifact for binding truth and workflow selection.
4. Advance the bound run only as needed, then inspect spec-freeze, product outputs, docs, screenshots, and acceptance artifacts.
5. Run workflow checks and canonical doc-only verify, record the first failure point if any, and close with a grounded rerun verdict.

## Notes / Decisions

- Default environment choice: `%TEMP%\ctcp_runs` because `D:\ctcp_runs` is not writable in this environment.
- Skill decision (`skillized: yes`): use `ctcp-workflow` for the scoped bind -> run -> verify -> report flow.
- Issue memory decision: carry forward the defect class as `rough_goal_domain_lift_can_still_underdeliver_even_when_entry_binds`.
- persona_lab_impact: none.

## Check / Contrast / Fix Loop Evidence

- check: the repaired support entry successfully bound fresh session `indie-domain-lift-rerun-20260423` to run `20260423-190306-801392-orchestrate`, and `find_result.json` selected `wf_project_generation_manifest`.
- contrast: the user-level expectation was a composite Indie Studio Hub domain with assets, bugs, build/release, docs-center coverage, dedicated milestone/startup/replay/mid-stage docs, and 10+ screenshots.
- fix: this turn is evidence-only, so no product-generation logic was changed; the run was advanced to completion and audited against the requested coverage gates instead of being “fixed” in-place.

## Completion Criteria Evidence

- completion criteria evidence: proved `connected + accumulated + consumed` for support entry -> bound run -> spec freeze -> generated project -> internal verify -> user-level acceptance review.
- connected: support session state persisted non-empty `active_goal`, `bound_run_id`, and `bound_run_dir`, and the run selected `wf_project_generation_manifest`.
- accumulated: the run produced `output_contract_freeze.json`, `project_spec.json`, generated project output, verify/delivery artifacts, and screenshot/doc evidence.
- consumed: the final verdict uses the real run artifacts to distinguish internal pass from user-level acceptance failure caused by domain collapse and coverage gaps.

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
- Verification summary: `support-entry rerun and artifact review passed; repo workflow_checks passed; canonical doc-only verify failed at module protection because of unrelated dirty/frozen-kernel files already present in the shared worktree`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
