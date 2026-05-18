# Demo Report - Minimal Planner Agent Loop

## Latest Report

- File: `meta/reports/archive/20260513-minimal-planner-agent-loop.md`
- Date: `2026-05-13`
- Topic: `Minimal Planner Agent Loop`

### Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `tools/agent_manifest_consumer.py`
- `tools/agent_scaffold_runtime_templates/runtime_engine.py.tpl`
- `tools/agent_scaffold_runtime_templates/runtime_planner.py.tpl`
- `tools/agent_scaffold_runtime_templates/runtime_tool_registry.py.tpl`
- `tests/test_agent_planner_loop.py`
- `tests/test_agent_planner_trace.py`
- `tests/test_agent_planner_permissions.py`
- `tests/test_agent_planner_final_answer.py`
- `tests/agent_planner_benchmark/run_planner_benchmark.py`
- `docs/agent_scaffold_mode.md`
- `docs/agent_project_pipeline.md`
- `README.md`

### Plan

1. Keep Phase 10 isolated to generated `agent-scaffold` / `agent-project` runtime.
2. Add generated `runtime_planner.py` with bounded deterministic planner and provider-interface failure path.
3. Route real run through planner while keeping policy as the only permission authority.
4. Persist `planner_trace.json`, final answer schema, audit evidence, and runtime_state planner metadata.
5. Add planner tests and planner benchmark covering research, feedback, devops, and permission_attack.
6. Update docs and run requested benchmarks, discovery, repo checks, and canonical verify.

### Changes

- Added generated planner runtime template: `tools/agent_scaffold_runtime_templates/runtime_planner.py.tpl`.
- Updated generated runtime engine template so real run calls the planner loop and returns `planner_mode`, `planner_trace_path`, and `final_answer`.
- Updated scaffold generation in `tools/agent_manifest_consumer.py` to emit `runtime/runtime_planner.py` and scaffold tests that verify `planner_trace.json`.
- Kept provider planner as an interface-only path: `CTCP_AGENT_PLANNER=provider` returns `provider_planner_unavailable` without fake success or external API calls.
- Kept default planner as deterministic: `CTCP_AGENT_PLANNER=deterministic`, max steps default `5`, configurable by `CTCP_AGENT_MAX_STEPS`.
- Added deterministic planner actions for research, product feedback/support, devops incident, and permission_attack tasks.
- Added exact local adapter mappings for feedback/support generated tools.
- Added planner tests and planner benchmark under `tests/agent_planner_benchmark/`.
- Updated `docs/agent_scaffold_mode.md`, `docs/agent_project_pipeline.md`, and `README.md`.

### Verify

- first failure point evidence: initial Phase 10 runtime benchmark failed because the synthetic unsupported-tool probe text contained the substring `support`, causing deterministic planner task routing to select support-style tools instead of the injected `unknown.synthetic` workflow tool.
- minimal fix strategy evidence: added an explicit unknown/synthetic probe path in `runtime_planner.py.tpl` so benchmark-injected unsupported workflow tools are passed through policy/executor and returned as unsupported ToolResult rows.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` ran inside canonical verify and passed.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` ran inside canonical verify and passed.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` ran inside canonical verify and passed.
- PASS: `.venv\Scripts\python.exe tests\agent_planner_benchmark\run_planner_benchmark.py` (`4/4`).
- PASS: `.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py` (`5/5`).
- PASS: `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py`.
  - phase1: `6/6`
  - semantic: `8/8`
  - holdout: `10/10`
  - phase4 e2e: `6/6`
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_planner_loop -v` (`4` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_planner_trace -v` (`3` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_planner_permissions -v` (`3` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_planner_final_answer -v` (`3` tests).
- PASS: `.venv\Scripts\python.exe -m unittest discover tests -v` (`707` tests, `4` skipped).
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py`.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json`.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py`.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`.

### Questions

- None.

### Demo

- Generated agents now run a bounded deterministic planner loop that observes ToolResult rows.
- Planner-selected tools still go through policy, ToolResult, audit, and state persistence.
- Research tasks complete with sources under the fixture web provider.
- Feedback/support tasks complete safe local drafts.
- Devops and permission_attack risky actions are blocked or pending approval and not claimed as executed.
- Ordinary CTCP project generation remains isolated.

### Reports

- Planner benchmark report: `tests/agent_planner_benchmark/benchmark_report.md`
- Runtime benchmark report: `tests/agent_runtime_benchmark/benchmark_report.md`
- Agent factory benchmark report: `tests/agent_factory_benchmark/benchmark_report.md`
