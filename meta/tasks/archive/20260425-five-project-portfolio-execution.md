# Task - Five-Project Portfolio Execution

## Queue Binding

- Queue Item: `ADHOC-20260425-five-project-portfolio-execution`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the user supplied a concrete five-project queue and explicitly asked CTCP to process it serially into real delivery artifacts instead of stopping at capability work.
- Lane: Delivery Lane for the repo task itself, because this task executes the existing portfolio-generation path and records external run evidence rather than changing product/runtime code again.
- Scope boundary: bind the exact user queue, run the current serial project-generation path in an external run_dir, inspect outputs, and report the strongest deliverable for every project plus the portfolio summary.

## Task Truth Source (single source for current task)

- task_purpose:
  - execute the exact five-project rough-goal queue through the current serial portfolio-generation path
  - keep runtime artifacts outside the repo in one external run_dir
  - inspect per-project artifacts, bundle paths, status fields, and final portfolio summary
  - report current strongest deliverable status for every project even if some subprojects are partial
- routed_bug_class:
  - project-generation execution and delivery evidence capture
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260425-project-queue-portfolio-mainline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-project-queue-portfolio-mainline.md`
- forbidden_goal_shift:
  - do not reopen the runtime implementation scope in this execution task
  - do not change the user’s five project goals
  - do not move runtime outputs into repo-owned artifact folders
  - do not stop after the first partial/failing project; all five must be processed
- in_scope_modules:
  - queue/task/report/archive bookkeeping
  - external run_dir creation and execution
  - portfolio artifact inspection and result reporting
- out_of_scope_modules:
  - new code refactors
  - support routing changes
  - benchmark/golden maintenance
- completion_evidence:
  - one external run_dir exists for the five-project queue
  - portfolio summary files exist and enumerate all five projects
  - every project has a strongest-available final bundle/evidence bundle path or an explicit recorded gap

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260425-project-queue-portfolio-mainline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-project-queue-portfolio-mainline.md`
  - `AGENTS.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/41_low_capability_project_generation.md`
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
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_prompt_contract_check.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
- Protected Paths:
  - any runtime output path inside the repo
  - unrelated implementation files outside the shared dirty ownership surface above
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `Five-Project Portfolio Execution inherits the already-dirty lane-owned and frozen-kernel shared worktree on 2026-04-25 so repo-level protection checks remain auditable while this task itself only updates meta bookkeeping and produces runtime evidence outside the repo`
- Forbidden Bypass:
  - no skipping projects after a partial result
  - no repo-local fake portfolio summary in place of real external run artifacts
  - no manual result claims without artifact inspection
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python scripts/module_protection_check.py`
  - `python scripts/workflow_checks.py`
  - `portfolio execution command via local Python entry using tools.providers.project_generation_artifacts`
  - `artifact inspection for portfolio summary and per-project bundles`

## Analysis / Find (before plan)

- Entrypoint analysis: run the current provider entrypoints directly against one external run_dir so the user gets real generated artifacts without waiting for repo refactors.
- Downstream consumer analysis: the result must include `portfolio_summary.json`, `portfolio_summary.md`, and per-project bundle/evidence paths plus verify/delivery summaries.
- Source of truth:
  - `AGENTS.md`
  - `.agents/skills/ctcp-workflow/SKILL.md`
  - `.agents/skills/ctcp-gate-precheck/SKILL.md`
  - `docs/12_virtual_team_contract.md`
  - `docs/25_project_plan.md`
  - `docs/41_low_capability_project_generation.md`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
- Current break point / missing wiring: execution is now the priority; code health debt from the previous task remains known but does not block external artifact generation for this user run.
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: the queued portfolio-generation path already exists and passed targeted regression coverage.
- current_module: external execution plus artifact inspection.
- downstream: the user needs a portfolio-level summary and per-project delivery paths, not another capability discussion.
- source_of_truth: external run artifacts produced by the current provider path.
- fallback: if any subproject cannot fully pass, keep its strongest bundle/evidence outputs and record `PARTIAL` or `NEEDS_REWORK` with the first failure point.
- acceptance_test:
  - run the five-project queue through the local provider path
  - inspect portfolio summary and each project directory for required outputs
  - refresh task/report evidence and status fields
- forbidden_bypass:
  - do not ask for page maps or data models
  - do not stop after one project
  - do not collapse internal PASS and user PASS
- user_visible_effect: the user gets one real portfolio run with five serial project outputs and an auditable summary.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: A real external run_dir is created for the five-project queue and binds the exact user-supplied rough goals into one serial portfolio request.
- [x] DoD-2: The current queue-generation path produces per-project artifact directories, strongest-available project bundles, evidence bundles, and dual-layer status fields for all five projects.
- [x] DoD-3: The final report records the external run_dir, portfolio summary paths, each project's final bundle/evidence bundle path, internal_runtime_status, user_acceptance_status, first_failure_point, and final verdict.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local readlist above)
- [x] Code changes allowed
- [x] External run executed and inspected
- [x] `scripts/verify_repo.*` pass status or first failure + minimal fix recorded
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Rebind the repo task from capability work to real five-project execution.
2. Create an external run_dir and materialize the exact user queue into `artifacts/frontend_request.json`.
3. Run `normalize_output_contract_freeze`, `normalize_source_generation`, `normalize_project_manifest`, and `normalize_deliverable_index`.
4. Inspect portfolio summary plus every project directory for artifacts, bundle paths, and status fields.
5. Refresh `meta/reports/LAST.md` with run evidence, first failure point, and strongest current deliverables.

## Notes / Decisions

- Default choices made: one clarification round is recorded per project as written questions plus explicit defaults; execution continues without waiting for answers.
- Alternatives considered: using the support-bot/orchestrator path was rejected for this turn because the provider entrypoints already produce the required generation artifacts more directly and deterministically.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - `None`
- Issue memory decision: no new issue-memory entry; this is a run execution task, not a newly observed recurring user-visible defect class.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because this run execution is one concrete user batch, not a new reusable repo workflow.`
- persona_lab_impact: `none`

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260425-project-queue-portfolio-mainline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-project-queue-portfolio-mainline.md`
- External run evidence:
  - run_dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\five_project_portfolio_20260425_144605`
  - portfolio summary JSON: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\five_project_portfolio_20260425_144605\project_output\portfolio-5-portfolio\portfolio_run\portfolio_summary.json`
  - portfolio summary Markdown: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\five_project_portfolio_20260425_144605\project_output\portfolio-5-portfolio\portfolio_run\portfolio_summary.md`
  - final package: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\five_project_portfolio_20260425_144605\artifacts\final_project_bundle.zip`
  - evidence bundle: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\five_project_portfolio_20260425_144605\artifacts\intermediate_evidence_bundle.zip`
- Execution summary:
  - the provider path processed all five queued projects serially and produced independent `00_intake` / `01_freeze` / `02_design` / `03_build` / `04_verify` / `05_delivery` directories plus `acceptance` triplets for each project
  - artifact-level runtime status is `PASS` for all five projects, but product-fit audit shows only projects 1 and 3 clearly match the requested product shape; projects 2, 4, and 5 remain strongest-current deliverables with user-fit gaps
- Verification summary:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` first failed at workflow gate because `meta/reports/LAST.md` had not yet recorded this task's triplet command evidence
  - after rerunning triplet commands and updating the report, the environment-specific `D:\ctcp_runs` permission issue was isolated and worked around by overriding `CTCP_RUNS_ROOT` to `%TEMP%\ctcp_runs` for runtime-wiring validation
  - `python scripts/workflow_checks.py`, `python scripts/module_protection_check.py`, `python scripts/prompt_contract_check.py`, `python scripts/plan_check.py`, `python scripts/patch_check.py`, `python scripts/behavior_catalog_check.py`, `python scripts/contract_checks.py`, `python scripts/sync_doc_links.py --check`, `python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`, and `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` all passed after the report refresh
  - full canonical `verify_repo.ps1` reruns with `%TEMP%\\ctcp_runs` timed out in the shared workspace before a final pass/fail conclusion was emitted, so repo-level final acceptance remains long-run inconclusive even though all pre-unit preverify gates checked here are green
- Queue status update suggestion (`todo/doing/done/blocked`): `done`

## Check / Contrast / Fix Loop Evidence

- check: the current provider path already passed the targeted queue-generation regression, so this task can focus on real run execution and artifact inspection.
- contrast: repo canonical verify is still known-blocked by code-health growth guard from the prior capability task, but that does not prevent one external generation run for the user’s queue.
- fix: execute the user batch externally now, and if runtime generation itself fails, record the first failing project/stage and strongest deliverable instead of stopping.

## Completion Criteria Evidence

- completion criteria evidence: must prove `connected + accumulated + consumed` for this five-project run.
- connected: the exact five rough goals are bound into one serial portfolio request in the external run_dir.
- accumulated: each project directory retains its own intermediate artifacts, verify summary, and bundle paths.
- consumed: the final portfolio summary enumerates those project results and the report cites the real run paths.
