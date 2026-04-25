# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-25`
- Topic: `Formal API-Only Execution Lock`
- Mode: `formal mainline provider lock + audit ledger hardening`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/25_project_plan.md`
- `docs/45_formal_benchmarks.md`
- `docs/46_benchmark_pass_contracts.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `llm_core/dispatch/router.py`
- `ctcp_adapters/ctcp_artifact_normalizers.py`
- `scripts/ctcp_dispatch.py`
- `scripts/ctcp_orchestrate.py`
- `scripts/ctcp_support_bot.py`
- `scripts/formal_benchmark_runner.py`
- `tools/providers/project_generation_source_stage.py`

### Plan
1. Archive the previous active task/report and bind the formal API-only execution-lock task.
2. Add a formal-mode switch and fail-fast provider enforcement in router/dispatch/orchestrate/support.
3. Block formal success paths that still rely on local fallback or local artifact normalizer synthesis.
4. Emit a provider ledger and expose API coverage in formal benchmark and portfolio summaries.
5. Add focused regressions, run targeted checks, then run canonical verify and record the first failure if any.

### Changes
- Archived the previous active task/report to:
  - `meta/tasks/archive/20260425-five-project-portfolio-execution.md`
  - `meta/reports/archive/20260425-five-project-portfolio-execution.md`
- Bound the new queue item:
  - `ADHOC-20260425-formal-api-only-execution-lock`
- Updated:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Added `tools/formal_api_lock.py`:
  - `CTCP_FORMAL_API_ONLY=1` switch
  - local exception locked to `librarian/context_pack`
  - run-level provider ledger append + summary generation
- Hardened formal mainline execution:
  - `llm_core/dispatch/router.py` blocks non-librarian non-`api_agent` provider selection in formal mode instead of silently remapping it to success
  - `scripts/ctcp_dispatch.py` fail-fast returns `provider_mismatch`, disables formal patchmaker local fallback, and writes provider-ledger rows for dispatch attempts
  - `llm_core/providers/api_provider.py` blocks local fallback/local plan fallback for formal API-required roles and records local function usage when fallback happens outside formal mode
  - `ctcp_adapters/ctcp_artifact_normalizers.py` forbids local JSON synthesis for formal project-generation artifacts such as freeze/source_generation/docs_generation/workflow_generation/manifest/deliver
  - `scripts/ctcp_orchestrate.py` skips manual fixer outbox creation in formal mode
  - `scripts/ctcp_support_bot.py` restricts formal support generation to `api_agent`, writes provider-ledger rows for `support_lead/support_reply`, and fails stdin-mode formal replies when provider execution or fallback rules are violated
- Exposed API coverage in formal reporting:
  - `scripts/formal_benchmark_runner.py` enables `CTCP_FORMAL_API_ONLY=1`, evaluates PASS against provider-ledger API coverage, emits coverage in JSON/Markdown summaries, and archives ledger artifacts into goldens
  - `tools/providers/project_generation_source_stage.py` surfaces per-project `api_coverage` in portfolio rows and Markdown summaries
  - `tools/providers/project_generation_artifacts.py` includes provider-ledger artifacts in evidence bundles
- Added focused regressions covering:
  - librarian local exception
  - non-librarian formal provider mismatch failure
  - no formal PASS through local patchmaker fallback
  - provider-ledger generation and summary gating
  - blocked local normalizer synthesis during formal project generation
- Updated docs:
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - both now state that formal benchmark/portfolio/endurance default to `CTCP_FORMAL_API_ONLY=1`, only librarian/context_pack is exempt, and PASS requires provider-ledger API coverage

### Verify
- Passed:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_plane_lite_benchmark_regression.py" -v`
  - `python -m unittest discover -s tests -p "test_formal_benchmark_runner.py" -v`
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/module_protection_check.py`
- `python scripts/workflow_checks.py`
- First failure point observed before final verify:
  - `test_runtime_wiring_contract.py` initially failed under the inherited default runs root with `[WinError 5]` on `D:\ctcp_runs`
- Minimal fix strategy:
  - set `CTCP_RUNS_ROOT` to a writable temp directory before runtime-wiring and canonical verify runs, because the failure was environmental rather than caused by the formal API-only patch
- Canonical verify:
  - `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - result: `FAIL`
  - first failure point: `code health growth-guard`
  - failure detail:
    - growth-guard rejected oversized or still-growing entrypoint/test files including `scripts/ctcp_dispatch.py`, `scripts/ctcp_orchestrate.py`, `scripts/ctcp_support_bot.py`, `tests/test_formal_benchmark_runner.py`, `tests/test_project_generation_artifacts.py`, and `tools/providers/project_generation_source_stage.py`
  - minimal fix strategy:
    - split or shrink the oversized entrypoint/test surfaces so the repo's file-size and longest-function thresholds are met, or move newly added enforcement/reporting helpers out of the guarded hot files into smaller modules

### Questions
- None.

### Demo
- Goal:
  - formal project-generation mainline is API-only except librarian/context_pack
  - non-API formal steps fail fast
  - provider ledger makes each critical step auditable
- Provider ledger fields now emitted per run:
  - `role`
  - `action`
  - `provider_used`
  - `external_api_used`
  - `request_id`
  - `fallback_used`
  - `local_function_used`
  - `verdict`
- API coverage consumption:
  - benchmark summaries now require `provider_ledger_summary.all_critical_steps_api=true`
  - portfolio summaries now show each sub-run's `critical_api_step_count / critical_step_count`
  - evidence bundles and golden archives preserve both provider-ledger artifacts for later audit
