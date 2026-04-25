# Task - Endurance Benchmark Formalization

## Queue Binding

- Queue Item: `ADHOC-20260425-endurance-benchmark-formalization`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the Indie Studio Production Hub Endurance run has already passed as a real experiment, but it still lacks a stable formal entrypoint and a focused golden archive for repeatable regression comparisons.
- Lane: Delivery Lane for the repo task itself, because this is a bounded benchmark formalization and archiving change inside the existing benchmark infrastructure.
- Scope boundary: standardize the endurance benchmark entry and PASS golden only; do not change support routing, domain-lift logic, benchmark pass rules, or product-generation behavior.

## Task Truth Source (single source for current task)

- task_purpose:
  - add a formal endurance benchmark entrypoint that can run, summarize, and archive the endurance regression without hand-built command chains
  - archive the known PASS endurance run into a focused golden set under `artifacts/benchmark_goldens/`
  - emit a stable JSON + Markdown benchmark summary with key run, delivery, and verdict fields
  - validate the entrypoint in summarize/archive-golden mode against the existing PASS run and keep repo gates green
- routed_bug_class:
  - benchmark formalization and golden-archive standardization
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260424-project-package-name-sanitization-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260424-project-package-name-sanitization-repair.md`
  - `AGENTS.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/42_frontend_backend_separation_contract.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `docs/50_prompt_hierarchy_contract.md`
  - `frontend/conversation_mode_router.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/classify_change_profile.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_bridge_views.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/formal_benchmark_runner.py`
  - `scripts/module_protection_check.py`
  - `scripts/prompt_contract_check.py`
  - `scripts/run_formal_endurance_benchmark.ps1`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `scripts/workflow_checks.py`
  - `templates/benchmark_summary_template.json`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/test_formal_benchmark_runner.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_prompt_contract_check.py`
  - `tests/test_runtime_wiring_contract.py`
  - `artifacts/benchmark_goldens/endurance_indie_studio_hub/**`
- forbidden_goal_shift:
  - do not change project-generation product logic
  - do not change support-entry routing or task binding
  - do not reopen domain-lift design work
  - do not mix repo hygiene or module-protection cleanup into this task
  - do not redefine benchmark pass standards
- in_scope_modules:
  - queue/task/report/archive bookkeeping
  - formal benchmark runner profile/wrapper behavior
  - benchmark docs and summary template
  - endurance golden archive files
  - focused runner tests
- out_of_scope_modules:
  - product-generation implementation
  - support entry logic
  - benchmark domain/pass criteria changes
  - unrelated repo cleanup
- completion_evidence:
  - a fixed endurance benchmark entrypoint exists and prints key paths/verdict fields
  - the existing PASS run can be summarized and archived into a focused golden set
  - golden contents include freeze, source generation, verify, delivery, final/evidence bundles, screenshots, api calls, and summary artifacts
  - repo verification gates remain green

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260424-project-package-name-sanitization-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260424-project-package-name-sanitization-repair.md`
  - `AGENTS.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/42_frontend_backend_separation_contract.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `docs/50_prompt_hierarchy_contract.md`
  - `frontend/conversation_mode_router.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/classify_change_profile.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_bridge_views.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/formal_benchmark_runner.py`
  - `scripts/module_protection_check.py`
  - `scripts/prompt_contract_check.py`
  - `scripts/run_formal_endurance_benchmark.ps1`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `scripts/workflow_checks.py`
  - `templates/benchmark_summary_template.json`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/test_formal_benchmark_runner.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_prompt_contract_check.py`
  - `tests/test_runtime_wiring_contract.py`
  - `artifacts/benchmark_goldens/endurance_indie_studio_hub/**`
- Protected Paths:
  - product-generation provider logic outside the benchmark runner surface
  - `agent_league_cases/**`
  - any file outside the allowed write paths above
- Frozen-kernel ownership inherited from the previous protection-zone task; this task does not edit frozen-kernel content but must keep those already-dirty paths in scope so shared-worktree verify remains stable.
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `Endurance Benchmark Formalization inherits the already-dirty protection-zone ownership from ADHOC-20260424-protection-zone-hygiene so repo verify remains stable while this task changes only benchmark entry/golden assets plus task/report bookkeeping on 2026-04-25`
- Forbidden Bypass:
  - no mock provider may be counted as a formal benchmark PASS
  - no benchmark summary may infer missing artifacts as present
  - no full run_dir dump may replace the focused golden archive
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_formal_benchmark_runner.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1 -Mode summarize -RunDir C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate`
  - `powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1 -Mode archive-golden -RunDir C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate`
  - `python scripts/module_protection_check.py`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`

## Analysis / Find

- Source of truth:
  - `AGENTS.md`
  - `.agents/skills/ctcp-gate-precheck/SKILL.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `docs/03_quality_gates.md`
  - `docs/25_project_plan.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `scripts/formal_benchmark_runner.py`
  - existing formal benchmark wrappers and goldens
  - the PASS endurance support session and run under `%TEMP%\ctcp_runs\ctcp\`
- Current break point / missing wiring:
  - no formal endurance benchmark profile/entrypoint exists yet
  - no focused golden archive exists for the PASS endurance run
- Repo-local search sufficient: `yes`; the PASS run already contains the runtime truth to archive.

## Integration Check

- upstream: the package-name repair task closed the endurance benchmark run successfully.
- current_module: formal benchmark entrypoints, summary generation, golden archiving.
- downstream: future regressions can use one fixed endurance entry and compare against a stable golden.
- source_of_truth: existing formal benchmark runner contracts plus the PASS endurance run artifacts.
- fallback: if summarize/archive-golden cannot prove the PASS run cleanly, stop at the first missing artifact and report it precisely.
- acceptance_test:
  - summary contains run/session paths, provider summary, freeze fields, key delivery verdicts, and bundle paths
  - golden archive preserves focused benchmark-comparison artifacts only
  - wrapper entry works in summarize and archive-golden modes against the PASS run
  - repo gates remain green
- forbidden_bypass:
  - no manual summary assembled outside the runner path
  - no whole-run copy used as the golden archive
  - no repo-level hygiene work mixed into this task
- user_visible_effect: endurance benchmark becomes repeatable and comparable instead of remaining a one-off successful run.

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: A fixed formal endurance benchmark entrypoint exists and can run/summarize/archive without manual command assembly.
- [ ] DoD-2: The PASS endurance run is archived into a focused golden set with stable summary files.
- [ ] DoD-3: Minimal validation and canonical repo gates pass, and the final report records the entrypoint/golden locations plus any remaining limits.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `existing formal benchmark runner/golden structure + PASS endurance run artifacts`
- [x] Code changes allowed
- [x] Implementation patched
- [x] Regression tests added and passing
- [x] Formal summarize/archive-golden validation completed
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Archive the previous package-name repair task/report and bind the formalization task.
2. Extend the formal benchmark runner with an `endurance` profile, summary fields, and focused golden-copy rules.
3. Add the PowerShell endurance wrapper and update the benchmark docs/template.
4. Add focused runner tests.
5. Summarize and archive the existing PASS endurance run through the new entrypoint.
6. Run repo verification gates and write the final formalization verdict.

## Issue Memory Decision

- decision: no new issue-memory entry.
- rationale: this task standardizes benchmark assets and does not introduce or repair a recurring user-visible defect.

## Skill Decision

- skillized: no, because this workflow remains tightly local to the repo’s existing formal benchmark surface and is best kept inside the current benchmark runner instead of introducing a new reusable skill layer.

## Notes / Decisions

- The golden source run is the known PASS rerun: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate`.
- The corresponding support session is `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\support_sessions\indie-studio-endurance-sanitized-20260424`.
- Minimal validation uses `summarize` and `archive-golden` modes rather than launching a new full API run.
- persona_lab_impact: none; this task does not change support style or dialogue contracts.

## Check / Contrast / Fix Loop Evidence

- check: the PASS endurance run already proves the product-generation mainline; what is missing is a stable benchmark entry and golden archive.
- contrast: this task standardizes existing benchmark assets instead of reopening generation logic.
- fix: extend the formal benchmark runner/profile surface and archive the already-PASS run into a focused golden set.

## Completion Criteria Evidence

- completion criteria evidence: must prove `connected + accumulated + consumed` for the endurance formalization path.
- connected: the new wrapper calls the formal benchmark runner with the endurance profile and prints benchmark summary fields.
- accumulated: the golden archive stores the focused PASS endurance artifacts and summary files in a stable repo location.
- consumed: minimal validation and the final report point to those runner/golden artifacts as the official endurance benchmark entry.

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260424-project-package-name-sanitization-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260424-project-package-name-sanitization-repair.md`
  - `scripts/formal_benchmark_runner.py`
  - `scripts/run_formal_endurance_benchmark.ps1`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `templates/benchmark_summary_template.json`
  - `tests/test_formal_benchmark_runner.py`
  - `artifacts/benchmark_goldens/endurance_indie_studio_hub/*`
- Verification summary:
  - focused runner tests: `PASS`
  - summarize mode against PASS endurance run: `PASS`
  - archive-golden mode against PASS endurance run: `PASS`
  - `python scripts/module_protection_check.py`: `PASS`
  - `python scripts/workflow_checks.py`: `PASS`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`: `PASS`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
