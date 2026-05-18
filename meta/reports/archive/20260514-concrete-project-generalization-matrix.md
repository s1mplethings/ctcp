# CTCP Report: Concrete Project Generalization Matrix

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-doc-index-sync/SKILL.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/api_agent.py`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_generic_materializers.py`
- `tools/providers/project_generation_issue_tracker_fast_path.py`
- `tools/providers/project_generation_matrix_fast_paths.py`
- `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
- `tests/concrete_project_matrix/run_matrix_benchmark.py`

### Plan
- Bind the Phase 12 matrix task and keep agent runtime/planner lines isolated.
- Add three distinct concrete project categories: Todo REST API, Markdown Notes API, and Simple Auth API.
- Keep all matrix cases inside ordinary `new-run/status/advance -> analysis -> source_generation -> project_output`.
- Validate generated tests, live HTTP endpoints, persistence, provenance, and no agent scaffold substitution.

### Changes
- Added matrix fast path detection/materialization for `todo_rest_api`, `markdown_notes_api`, and `simple_auth_api`.
- Extended output contract/source generation provenance so matrix runs write `artifacts/project_generation_provenance.json`.
- Added `tests/concrete_project_matrix/` fixtures, matrix runner, generated summary/report output, and runtime validators.
- Added focused tests for matrix contract, Todo CRUD, Notes filesystem markdown, and Auth protected endpoint/session behavior.
- Added docs for concrete project generation and the concrete pipeline matrix.

### Verify
- `.\.venv\Scripts\python.exe tests\concrete_project_matrix\run_matrix_benchmark.py` -> PASS, `3/3`.
- `.\.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_concrete_project_matrix -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_todo_api_generation -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_notes_api_generation -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_auth_api_generation -v` -> PASS.
- `.\.venv\Scripts\python.exe tests\agent_planner_benchmark\run_planner_benchmark.py` -> PASS `4/4`.
- `.\.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py` -> PASS `5/5`.
- `.\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest discover tests -v` -> PASS, `724` tests, `4` skipped.
- `.\.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> PASS.
- `.\.venv\Scripts\python.exe scripts\patch_check.py` -> PASS.
- `.\.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> PASS.
- `.\.venv\Scripts\python.exe scripts\sync_doc_links.py --check` -> PASS.

First failure point evidence:
- Initial matrix runner used `advance --max-steps 3`; the Todo run timed out while ordinary review gates were progressing. Minimal fix: advance one step at a time and preserve status evidence between steps.
- Initial generated Todo/Auth SQLite stores left Windows DB handles open because `sqlite3.Connection` context manager does not close connections. Minimal fix: generated stores use a closing context manager and explicit commits.
- Initial matrix Auth validator opened a suffixless evidence path instead of the actual `*.db` file passed to the server. Minimal fix: validator returns and checks the actual persistence path.
- Latest workflow check found task/report evidence fields incomplete. Minimal fix: update `CURRENT.md` and `LAST.md` with mandatory integration and triplet evidence fields.

Minimal fix strategy evidence:
- Keep repairs inside matrix materializer, validator, task card, and report files.
- Preserve ordinary orchestration and validate behavior through real generated tests, HTTP requests, and persistence checks.
- Do not change agent runtime/planner implementation or benchmark fixtures.

Triplet runtime wiring command evidence:
- Matrix command exercises ordinary `new-run/status/advance`, generated `app.py --host --port`, endpoint probes, and persistence validation.
- Runtime wiring validated by `tests/concrete_project_matrix/run_matrix_benchmark.py` plus focused Todo/Notes/Auth runtime tests.
- Related contract regression reference: `tests/test_runtime_wiring_contract.py`.

Triplet issue memory command evidence:
- Current issue memory decision: no new reusable lesson file; repair details are captured in this report and benchmark reports.
- Evidence source: focused failures were fixed by materializer/validator changes, not by changing fixtures or skipping gates.
- Related contract regression reference: `tests/test_issue_memory_accumulation_contract.py`.

Triplet skill consumption command evidence:
- Used `ctcp-workflow` for binding, scoped implementation, verification, and report discipline.
- Used `ctcp-doc-index-sync` check flow via `.\.venv\Scripts\python.exe scripts\sync_doc_links.py --check`.
- Related contract regression reference: `tests/test_skill_consumption_contract.py`.

### Questions
- None.

### Demo
- Matrix benchmark report: `tests/concrete_project_matrix/benchmark_report.md`.
- Matrix summary: `tests/concrete_project_matrix/generated/matrix_summary.json`.
- Existing concrete report: `tests/concrete_project_benchmark/benchmark_report.md`.
