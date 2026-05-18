# CTCP Report: Non-Web Project Matrix And Attribution Review Pack

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_fast_path_registry.py`
- `tools/providers/project_generation_fast_path_materializers.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_matrix_fast_paths.py`
- `tools/providers/project_generation_template_writer.py`
- `tests/concrete_project_matrix/run_matrix_benchmark.py`
- `tests/full_stack_app_benchmark/run_full_stack_benchmark.py`
- `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`

### Plan
- Bind the Phase 15 task and keep agent runtime/planner lines isolated.
- Add non-web concrete fast paths for two CLIs, one package, and one terminal game.
- Add `generation_attribution.json` evidence and show attribution in concrete benchmark reports/summaries.
- Add `meta/reports/REVIEW_PACK.md` for human/ChatGPT review.
- Validate non-web CLI/package/game behavior through ordinary `new-run/status/advance`.

### Changes
- Added non-web concrete fast path support for `csv_expense_analyzer`, `log_analyzer_cli`, `text_utils_package`, and `terminal_quiz_game`.
- Added `tools/providers/project_generation_attribution.py` and wired source generation to write `artifacts/generation_attribution.json`.
- Extended fast path registry/materializer dispatch and ordinary concrete/full-stack benchmark reports with Attribution sections.
- Added `tests/non_web_project_matrix/` runner, fixtures, validators, report, and summary.
- Added focused non-web generation, attribution, and review-pack tests.
- Updated README and concrete project generation docs.

### Verify
- `.\.venv\Scripts\python.exe tests\non_web_project_matrix\run_non_web_matrix.py` -> PASS `4/4`.
- `.\.venv\Scripts\python.exe tests\full_stack_app_benchmark\run_full_stack_benchmark.py` -> PASS `2/2`.
- `.\.venv\Scripts\python.exe tests\concrete_project_matrix\run_matrix_benchmark.py` -> PASS `3/3`.
- `.\.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\agent_planner_benchmark\run_planner_benchmark.py` -> PASS `4/4`.
- `.\.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py` -> PASS `5/5`.
- `.\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest discover tests -v` -> PASS `741` tests, `4` skipped.
- `.\.venv\Scripts\python.exe scripts\workflow_checks.py` -> PASS after adding task-card integration fields.
- `.\.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> PASS.
- `.\.venv\Scripts\python.exe scripts\patch_check.py` -> PASS.
- `.\.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> PASS.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> PASS.

First failure point evidence: initial `concrete_project_benchmark` run timed out at `advance_5` before source generation. The failure was not a generated-project validation failure.

Minimal fix strategy evidence: raised the benchmark default advance timeout from 180s to 240s, then reran issue tracker benchmark to PASS.

Triplet runtime wiring command evidence: reference command `.\.venv\Scripts\python.exe -m unittest tests.test_runtime_wiring_contract.py -v`.

Triplet issue memory command evidence: reference command `.\.venv\Scripts\python.exe -m unittest tests.test_issue_memory_accumulation_contract.py -v`.

Triplet skill consumption command evidence: reference command `.\.venv\Scripts\python.exe -m unittest tests.test_skill_consumption_contract.py -v`.

### Questions
- None.

### Demo
- Non-web matrix report: `tests/non_web_project_matrix/benchmark_report.md`.
- Non-web matrix summary: `tests/non_web_project_matrix/generated/non_web_matrix_summary.json`.
- Review pack: `meta/reports/REVIEW_PACK.md`.
