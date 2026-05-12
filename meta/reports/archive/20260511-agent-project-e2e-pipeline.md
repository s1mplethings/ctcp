# Demo Report - End-to-End Agent Project Pipeline Integration

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_orchestrate.py`
- `tools/agent_manifest_consumer.py`
- `tests/agent_factory_benchmark/run_benchmark.py`
- `tests/test_agent_project_pipeline.py`
- `tests/test_agent_project_orchestrator_e2e.py`
- `README.md`
- `docs/agent_manifest_mode.md`
- `docs/agent_scaffold_mode.md`

## Plan
1. Bind a Delivery Lane task with fixtures, validators, generator, and provider/core modules protected.
2. Add an e2e pipeline module for requirement -> manifest -> scaffold -> dry-run -> scaffold tests -> reports.
3. Add explicit `agent-project` orchestrator mode and independent scaffold script.
4. Add pipeline/orchestrator tests and upgrade benchmark Phase 4 to real e2e execution.
5. Update docs and run required gates plus canonical verify.

## Changes
- Added `tools/agent_project_pipeline.py`.
- Added `scripts/generate_agent_scaffold.py`.
- Updated `tools/agent_manifest_consumer.py` to write `audit/dry_run_audit.jsonl` and generate `test_dry_run.py`.
- Updated `scripts/ctcp_orchestrate.py` with explicit `agent-project` registration and dispatch.
- Added `tests/test_agent_project_pipeline.py` and `tests/test_agent_project_orchestrator_e2e.py`.
- Updated benchmark Phase 4 and wrote compact e2e evidence under `tests/agent_factory_benchmark/e2e_pipeline/`.
- Added `docs/agent_project_pipeline.md`; updated agent manifest/scaffold docs and README.
- Did not modify generator, fixtures, validators, or ordinary project-generation behavior.

## Verify
- PASS: `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` returned 0 with Phase 1 `6/6`, Phase 2 `8/8`, Holdout `10/10`, and Phase 4 e2e `6/6`.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_generator -v` returned 0, 23 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_orchestrator_integration -v` returned 0, 9 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_consumer -v` returned 0, 10 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_project_pipeline -v` returned 0, 10 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_project_orchestrator_e2e -v` returned 0, 9 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover tests -v` returned 0, 617 tests OK, skipped 4.
- PASS: triplet runtime wiring command evidence was executed by canonical verify: `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`.
- PASS: triplet issue memory command evidence was executed by canonical verify: `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`.
- PASS: triplet skill consumption command evidence was executed by canonical verify: `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`.
- PASS: `.venv\Scripts\python.exe -m py_compile tools\agent_manifest_consumer.py tools\agent_project_pipeline.py scripts\generate_agent_scaffold.py scripts\ctcp_orchestrate.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0.

## Questions
- None.

## Demo
- New command: `.\.venv\Scripts\python.exe scripts\ctcp_orchestrate.py agent-project --input <input.json> --output-dir <agent_project_dir>`.
- Independent manifest entrypoint remains: `scripts/generate_agent_manifest.py --input <input.json> --output <manifest.json>`.
- Orchestrator manifest entrypoint remains: `scripts/ctcp_orchestrate.py agent-manifest --input <input.json> --output <manifest.json>`.
- Scaffold mode remains: `scripts/ctcp_orchestrate.py agent-scaffold --manifest <manifest.json> --output-dir <dir>`.
- Phase 4 e2e cases all passed: devops incident, permission attack, H1 personal productivity, H2 patient intake, H9 battery charging, H10 product launch.
- Benchmark report: `tests/agent_factory_benchmark/benchmark_report.md`.

## Check/Contrast/Fix Loop Evidence
- check: focused tests initially failed on H1/H9/H10 domain checks.
- contrast: the checks were scanning global safety permissions and guardrails rather than executable capabilities.
- fix: domain checks now inspect agents/tools/workflows; regulated safety still inspects full guardrails.
- re-check: benchmark, focused tests, full discovery, gates, and canonical verify passed.

## Completion Criteria Evidence
- connected: `agent-project` reaches `tools.agent_project_pipeline`.
- accumulated: pipeline output includes manifest, scaffold, dry-run audit, scaffold tests, and reports.
- consumed: benchmark and tests execute the generated dry-run and generated scaffold tests.

## Issue Memory Decision Evidence
- no new issue-memory entry; the only failure was a local test-surface mismatch introduced and repaired in this task.

## Skill Decision
- skill used: `ctcp-workflow`.
- skillized: no, because this is a repo-local feature mode, not a reusable Codex workflow yet.
