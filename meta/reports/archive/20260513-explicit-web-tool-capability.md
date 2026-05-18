# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-05-13`
- Topic: `Explicit Web Tool Capability`

### Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `tools/agent_manifest_consumer.py`
- `tools/agent_manifest_generator.py`
- `tools/agent_scaffold_runtime_templates/runtime_tool_registry.py.tpl`
- `tools/agent_scaffold_runtime_templates/runtime_engine.py.tpl`
- `tests/agent_runtime_benchmark/run_runtime_benchmark.py`
- `tests/agent_runtime_benchmark/fixtures/research_agent_web.json`
- `tests/fixtures/web_search_fixture.json`
- `tests/test_web_tool_runtime_policy.py`
- `tests/test_web_tool_runtime_results.py`
- `tests/test_web_tool_runtime_audit.py`
- `tests/test_research_agent_web_benchmark.py`
- `docs/agent_scaffold_mode.md`
- `docs/agent_project_pipeline.md`
- `README.md`

### Plan

1. Keep Phase 9 isolated to explicit `agent-scaffold` / `agent-project` runtime generation.
2. Add manifest-only `web_search` and `fetch_url` adapters behind registry and policy checks.
3. Add deterministic fixture provider support with no production internet provider.
4. Require sources/citations for web-derived ToolResult output and audit query/url details.
5. Add research-agent fixture, focused web runtime tests, runtime benchmark assertions, and docs.
6. Run requested benchmarks, unit tests, repo checks, and canonical verify.

### Changes

- Updated `tools/agent_manifest_consumer.py` so generated scaffold supports explicit web-capable runtime modules while keeping default local deterministic behavior.
- Added generated runtime template files:
  - `tools/agent_scaffold_runtime_templates/runtime_tool_registry.py.tpl`
  - `tools/agent_scaffold_runtime_templates/runtime_engine.py.tpl`
- Added generated adapters for `web_search` and `fetch_url`; these execute only when the manifest declares the exact tool and policy allows the selected caller.
- Added fixture provider mode: `CTCP_AGENT_WEB_PROVIDER=fixture`, reading `tests/fixtures/web_search_fixture.json` or `CTCP_AGENT_WEB_FIXTURE_PATH`.
- Kept real internet provider out of scope: no production web/search provider or external API client was added.
- Updated generated web policy to deny unauthorized web tools with `web_permission_denied` and unknown web-like tools as unsupported.
- Updated ToolResult/source behavior so web results include `sources` or `source`; missing sources fail with `missing_sources`.
- Updated audit events to include web `query`, `url`, `sources`, and `audit_required` fields for web decisions.
- Updated `tools/agent_manifest_generator.py` to emit a `research_agent` manifest with `web_search`, `fetch_url`, `source_summary`, and `citation_builder` for explicit web research inputs.
- Added fixtures/tests:
  - `tests/fixtures/web_search_fixture.json`
  - `tests/agent_runtime_benchmark/fixtures/research_agent_web.json`
  - `tests/test_web_tool_runtime_policy.py`
  - `tests/test_web_tool_runtime_results.py`
  - `tests/test_web_tool_runtime_audit.py`
  - `tests/test_research_agent_web_benchmark.py`
- Extended `tests/agent_runtime_benchmark/` to cover `research_agent_web` and assert web ToolResult, audit, state, and non-research no-web behavior.
- Updated `docs/agent_scaffold_mode.md`, `docs/agent_project_pipeline.md`, and `README.md`.

### Verify

- first failure point evidence: first full canonical verify after implementation failed in python unit tests because `tests/test_research_agent_web_benchmark.py` used package-style import and verify's discover path imported it as a top-level test module.
- minimal fix strategy evidence: changed the test to import `run_runtime_benchmark.py` through an explicit filesystem path, then reran the targeted test, full discover, and canonical verify.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` ran inside canonical verify and passed.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` ran inside canonical verify and passed.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` ran inside canonical verify and passed.
- PASS: `.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py` (`5/5`; includes `research_agent_web`).
- PASS: `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py`.
  - phase1: `6/6`
  - semantic: `8/8`
  - holdout: `10/10`
  - phase4 e2e: `6/6`
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_web_tool_runtime_policy -v` (`6` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_web_tool_runtime_results -v` (`3` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_web_tool_runtime_audit -v` (`1` test).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_research_agent_web_benchmark -v` (`1` test).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_registry -v` (`4` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_policy -v` (`8` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_result_schema -v` (`2` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_audit_contract -v` (`3` tests).
- PASS: `.venv\Scripts\python.exe -m unittest discover tests -v` (`694` tests, `4` skipped).
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py`.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json`.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py`.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`.

### Questions

- None.

### Demo

- `web_search`: added as explicit manifest-only generated runtime adapter.
- `fetch_url`: added as explicit manifest-only generated runtime adapter.
- Default agent web access: no; non-research manifests do not declare web tools and cannot execute them.
- Fixture provider: yes; deterministic local provider enabled only by `CTCP_AGENT_WEB_PROVIDER=fixture`.
- Real internet provider: no.
- Web ToolResult sources/citations: yes; `web_search` returns `sources`, `fetch_url` returns `source`, and runtime output aggregates `sources`.
- Audit coverage: executed, blocked, unsupported, and failed web decisions write audit; query/url/source details are recorded when present.
- Permission attack safety: preserved; runtime benchmark and agent factory benchmark stayed pass.
- Ordinary CTCP project generation: unchanged; `new-run/status/advance` remain isolated from explicit agent runtime modes.

### Reports

- Runtime benchmark report: `tests/agent_runtime_benchmark/benchmark_report.md`
- Agent factory benchmark report: `tests/agent_factory_benchmark/benchmark_report.md`
