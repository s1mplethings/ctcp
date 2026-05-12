# Task - Analysis Prompt Slimming / Fast Analysis Mode

## Queue Binding

- Queue Item: `ADHOC-20260512-analysis-prompt-slimming-fast-mode`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: enter CTCP Phase 6.3 - Analysis Prompt Slimming / Fast Analysis Mode.
- Phase 6.2 localized the remaining benchmark failure to analysis provider timeout.
- Latest concrete benchmark: `failed`, `failure_stage=analysis`, `failure_reason=analysis_provider_timeout`, elapsed `92.645s`, `advance_1=91.087s`, `timeout_step=none`.
- This task must make `artifacts/analysis.md` a short, budgeted pre-source artifact without skipping the analysis gate or mocking provider success.

## Task Truth Source

- task_purpose:
  - Reduce analysis prompt size and output scope so `artifacts/analysis.md` can be generated within the existing 90 second guard.
  - Add `CTCP_ANALYSIS_PROFILE=fast` for a short provider prompt and explicit analysis output contract.
  - Record prompt budget metrics in `analysis_progress.json`.
  - Preserve real provider calls, real analysis gate, real benchmark execution, and Phase 6.2 timeout observability.
- allowed_behavior_change:
  - Add a fast analysis prompt/profile selected by environment or benchmark env.
  - Add prompt char/token/output-contract/max-output-token metrics.
  - Add short analysis output contract with bounded Markdown sections.
  - Add focused fast profile and prompt budget tests.
  - Configure the concrete benchmark to use fast analysis profile without changing fixture requirements.
- forbidden_goal_shift:
  - Do not skip the analysis gate.
  - Do not fake `artifacts/analysis.md`.
  - Do not mock provider success.
  - Do not hardcode the concrete benchmark case.
  - Do not modify benchmark fixtures.
  - Do not delete real provider generation.
  - Do not disable normal CTCP workflow gates.
  - Do not make timeouts infinite.
  - Do not modify unrelated frozen-kernel files.
- in_scope_modules:
  - `tools/analysis_fast_profile.py`
  - `tools/analysis_stage_progress.py`
  - `llm_core/providers/api_provider.py`
  - `llm_core/clients/openai_compatible.py`
  - `scripts/ctcp_orchestrate.py`
  - `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
  - `tests/test_analysis_fast_profile.py`
  - `tests/test_analysis_prompt_budget.py`
  - `tests/test_analysis_stage_progress.py`
  - `tests/test_analysis_stage_timeout.py`
  - `tests/test_analysis_stage_resume.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_api_provider_core.py`
  - `tests/concrete_project_benchmark/generated/issue_tracker_api/benchmark_summary.json`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - benchmark fixtures
  - provider credentials
  - unrelated frozen kernels outside analysis status/progress wiring
  - generated project output directories except through the generator/reconciliation flow
- completion_evidence:
  - focused tests and gate results in `meta/reports/LAST.md`
  - graph artifacts written by source_generation runs
  - first-failure evidence for benchmark/verify blockers

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/analysis_fast_profile.py`
  - `tools/providers/project_generation_contracts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/analysis_stage_progress.py`
  - `llm_core/providers/api_provider.py`
  - `llm_core/clients/openai_compatible.py`
  - `scripts/ctcp_orchestrate.py`
  - `tests/test_generation_consistency.py`
  - `tests/test_convergence_performance_guards.py`
  - `tests/test_analysis_stage_progress.py`
  - `tests/test_analysis_stage_timeout.py`
  - `tests/test_analysis_stage_resume.py`
  - `tests/test_analysis_fast_profile.py`
  - `tests/test_analysis_prompt_budget.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_api_provider_core.py`
  - `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
  - `tests/concrete_project_benchmark/benchmark_report.md`
  - `tests/concrete_project_benchmark/generated/issue_tracker_api/benchmark_summary.json`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260512-contract-graph-convergence-stabilization.md`
  - `meta/reports/archive/20260512-pre-source-analysis-timeout-repair.md`
- Protected Paths:
  - `.git`
  - provider credentials
  - benchmark fixtures
  - unrelated frozen kernels
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `Phase 6.3 owns analysis prompt slimming and status/progress evidence for artifacts/analysis.md without changing unrelated frozen-kernel behavior.`
- Forbidden Bypass:
  - no benchmark fixture edits
  - no fake analysis.md
  - no mocked provider success
  - no workflow gate disablement
  - no infinite timeout
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m py_compile tools\analysis_fast_profile.py tools\analysis_stage_progress.py llm_core\providers\api_provider.py llm_core\clients\openai_compatible.py scripts\ctcp_orchestrate.py tests\concrete_project_benchmark\run_concrete_project_benchmark.py`
  - `.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_analysis_fast_profile -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_analysis_prompt_budget -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_analysis_stage_progress -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_analysis_stage_timeout -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_analysis_stage_resume -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_generation_consistency -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_convergence_performance_guards -v`
  - `.venv\Scripts\python.exe -m unittest discover tests -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Existing Phase 6.1 benchmark evidence localizes timeout to `advance_1`.
- `current_gate()` waits for `artifacts/analysis.md` immediately after guardrails.
- `dispatch_request_mapper` maps missing `analysis.md` to role `chair`, action `plan_draft`, target `artifacts/analysis.md`.
- `llm_core.providers.api_provider` owns prompt rendering, provider subprocess execution, target normalization, and artifact writing.

## Plan

1. Add fast analysis profile renderer with short output contract.
2. Record prompt size/token/output-contract/max-output metrics in analysis progress.
3. Route fast analysis through real API agent stdin prompt rather than the larger default plan command.
4. Configure concrete benchmark env with `CTCP_ANALYSIS_PROFILE=fast`.
5. Add focused fast profile and prompt budget tests.
6. Run required benchmark, focused tests, discovery, and gates.

## Acceptance

- [ ] Fast profile is selected via `CTCP_ANALYSIS_PROFILE=fast`.
- [ ] Fast prompt is smaller than default prompt while retaining concrete project requirements.
- [ ] Fast output contract exists and is recorded.
- [ ] `analysis_progress.json` records prompt char count, token estimate, output contract, max output tokens, and analysis profile.
- [ ] Concrete benchmark no longer fails at analysis due prompt bloat; if it still fails, report includes prompt budget evidence.
- [ ] Focused fast profile and prompt budget tests pass.

## Integration Check

- upstream: `ctcp_orchestrate.py advance` blocked on `artifacts/analysis.md`.
- current_module: analysis-stage provider execution, normalization, artifact writing, status display, and benchmark report evidence.
- downstream: source_generation, generated tests, HTTP probes, SQLite validation, and contract graph convergence.
- source_of_truth: real run artifacts under `${run_dir}/artifacts/`, especially `analysis.md` and `analysis_progress.json`.
- fallback: analysis timeout blocks gracefully with raw/partial evidence and resume path.
- acceptance_test: focused analysis tests, concrete benchmark, discovery, and canonical verify.
- forbidden_bypass: no fake analysis artifact, no mocked provider success, no fixture edits.
- user_visible_effect: status and benchmark report reveal whether analysis is running, timed out, failed, resumable, or completed.

## Check/Contrast/Fix Loop Evidence

- check: benchmark now returns `failed` in `181.328s` with `timeout_step=advance_1`.
- contrast: status before timeout is waiting for `artifacts/analysis.md`; source generation has not started.
- fix: add analysis-stage progress, timeout containment, raw/partial preservation, resume, and benchmark evidence.
- re-check: pending.

## Completion Criteria Evidence

- connected + accumulated + consumed.
- connected: pending analysis-stage progress wiring.
- accumulated: pending analysis progress and benchmark summary/report evidence.
- consumed: pending status output and benchmark report consumption.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new issue-memory entry.
- reason: current first blocker is local analysis-stage timeout observability/containment, recorded in task/report evidence.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: Phase 6.2 timeout repair requires queue binding, scoped implementation, canonical verification, and report evidence.
- skillized: no.
