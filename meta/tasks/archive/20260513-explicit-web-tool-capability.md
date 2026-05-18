# Task - Explicit Web Tool Capability

## Queue Binding

- Queue Item: `ADHOC-20260513-explicit-web-tool-capability`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: enter CTCP Phase 9 - Explicit Web Tool Capability.
- Phase 7 completed the minimal generated agent runtime loop.
- Phase 8 completed generated tool registry, policy, executor, ToolResult, adapter interface, audit, and unsupported-tool handling.
- Current runtime has no web access. This phase may add explicit manifest-only web capability with a deterministic fixture provider, but must not claim real internet access.

## Task Truth Source

- task_purpose:
  - Add explicit manifest-authorized `web_search` and `fetch_url` runtime capability to generated scaffold.
  - Keep web access disabled by default for all agents.
  - Implement deterministic fixture web provider for tests through `CTCP_AGENT_WEB_PROVIDER=fixture`.
  - Preserve registry, policy, ToolResult, audit, state, permission_attack safety, and ordinary CTCP project generation isolation.
- required_runtime_chain:
  - `manifest tools[] -> normalize web contract -> policy check -> execute fixture web adapter if explicitly authorized -> ToolResult with sources -> audit query/url -> update runtime_state.json`.
- allowed_behavior_change:
  - Add generated web adapters and web policy rules.
  - Add deterministic fixture provider and fixture files.
  - Add research-agent benchmark/input coverage.
  - Update docs and tests.
- forbidden_goal_shift:
  - Do not add default web access.
  - Do not execute unknown web-like tools.
  - Do not bypass registry, policy, ToolResult, audit, or state.
  - Do not execute high-risk or external side-effect tools.
  - Do not run `web_search` or `fetch_url` unless manifest explicitly declares and authorizes them.
  - Do not return web-derived success without sources/citations.
  - Do not modify benchmark fixtures to lower difficulty.
  - Do not break Phase 7/8 runtime tests.
  - Do not break ordinary CTCP project generation.
- in_scope_modules:
  - `tools/agent_manifest_consumer.py`
  - `tools/agent_manifest_generator.py`
  - `tools/agent_scaffold_runtime_templates/**`
  - `tests/test_web_tool_runtime_policy.py`
  - `tests/test_web_tool_runtime_results.py`
  - `tests/test_web_tool_runtime_audit.py`
  - `tests/test_research_agent_web_benchmark.py`
  - `tests/test_tool_runtime_registry.py`
  - `tests/test_tool_runtime_policy.py`
  - `tests/test_tool_runtime_result_schema.py`
  - `tests/test_tool_runtime_audit_contract.py`
  - `tests/fixtures/web_search_fixture.json`
  - `tests/agent_runtime_benchmark/**`
  - `tests/agent_factory_benchmark/run_benchmark.py`
  - `tests/agent_factory_benchmark/benchmark_report.md`
  - `docs/agent_scaffold_mode.md`
  - `docs/agent_project_pipeline.md`
  - `README.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260513-explicit-web-tool-capability.md`
  - `meta/reports/archive/20260513-explicit-web-tool-capability.md`
- out_of_scope_modules:
  - production web/search provider integration
  - real external API clients
  - benchmark fixture weakening
  - semantic/holdout validator weakening
  - ordinary `new-run/status/advance` project generation behavior
  - permission attack protections
  - unrelated support/frontend/runtime wiring
- completion_evidence:
  - generated scaffold supports explicit web tools only when manifest declares and policy permits them.
  - fixture web provider returns cited sources.
  - provider unavailable fails safely with ToolResult and audit.
  - audit records query/url.
  - runtime_state records web ToolResult rows.
  - non-research and permission_attack cases do not gain web access.
  - required tests, benchmarks, discovery, checks, and canonical verify are recorded in `meta/reports/LAST.md`.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/agent_manifest_consumer.py`
  - `tools/agent_manifest_generator.py`
  - `tools/agent_scaffold_runtime_templates/`
  - `tests/test_web_tool_runtime_policy.py`
  - `tests/test_web_tool_runtime_results.py`
  - `tests/test_web_tool_runtime_audit.py`
  - `tests/test_research_agent_web_benchmark.py`
  - `tests/test_tool_runtime_registry.py`
  - `tests/test_tool_runtime_policy.py`
  - `tests/test_tool_runtime_result_schema.py`
  - `tests/test_tool_runtime_audit_contract.py`
  - `tests/fixtures/web_search_fixture.json`
  - `tests/agent_runtime_benchmark/`
  - `tests/agent_factory_benchmark/run_benchmark.py`
  - `tests/agent_factory_benchmark/benchmark_report.md`
  - `docs/agent_scaffold_mode.md`
  - `docs/agent_project_pipeline.md`
  - `README.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260513-explicit-web-tool-capability.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260513-explicit-web-tool-capability.md`
- Protected Paths:
  - `.git`
  - provider credentials
  - production web/search providers
  - benchmark fixtures except additive research/web fixtures
  - semantic/holdout validators except additive web runtime benchmark assertions
  - real external API clients
  - unrelated frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no default web access
  - no real internet provider claim
  - no fixture weakening
  - no fake web runtime success
  - no web-like unknown-tool execution
  - no unsupported-tool success
  - no approval bypass
  - no high-risk execution
  - no external side-effect execution
- Acceptance Checks:
  - `.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py`
  - `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_web_tool_runtime_policy -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_web_tool_runtime_results -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_web_tool_runtime_audit -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_research_agent_web_benchmark -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_registry -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_policy -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_result_schema -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_tool_runtime_audit_contract -v`
  - `.venv\Scripts\python.exe -m unittest discover tests -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Root contract requires current task as task-purpose authority.
- Web capability must be explicit and generated into scaffold runtime, not enabled globally.
- Fixture provider is local deterministic test infrastructure; it does not mean the agent can reach the real internet.
- Source/citation evidence is part of the web tool success contract.

## Plan

1. Extend generated tool registry to recognize only explicit `web_search` and `fetch_url` runtime adapters.
2. Extend generated policy to enforce web manifest authorization, caller allowlist, side-effect none, approval-free, and audit-required.
3. Add generated fixture web provider and web adapter execution with ToolResult/sources.
4. Record query/url and sources in `tool_decision` audit events.
5. Extend runtime benchmark with `research_agent_web` under `CTCP_AGENT_WEB_PROVIDER=fixture`.
6. Add focused web runtime tests and docs, then run required gates.

## Acceptance

- [x] `web_search` is supported only as explicit manifest tool.
- [x] `fetch_url` is supported only as explicit manifest tool.
- [x] Default/non-research agents have no web access.
- [x] Unknown web-like tools are unsupported or blocked, not executed.
- [x] Web policy denies caller mismatch, missing audit, approval-required, side-effect non-none, and missing manifest authorization.
- [x] Provider unavailable returns failed ToolResult and audit evidence.
- [x] Fixture provider returns sources/citations.
- [x] Web ToolResult includes sources or source.
- [x] Audit records query and url.
- [x] Permission attack remains safe.
- [x] Runtime benchmark includes and passes `research_agent_web`.
- [x] Agent factory benchmark remains pass.
- [x] Ordinary CTCP project generation remains isolated.

## Integration Check

- upstream: explicit `agent-scaffold` and `agent-project` subcommands only.
- current_module: generated scaffold web tool runtime contract.
- downstream: generated scaffold tests, focused web/tool tests, runtime benchmark, agent factory benchmark.
- source_of_truth: manifest tool contract, fixture provider file, ToolResult, `runtime_state.json`, `audit/events.jsonl`.
- fallback: unavailable or unauthorized web tools return failed/blocked ToolResult with audit evidence.
- acceptance_test: focused web runtime tests, runtime benchmark, agent factory benchmark, discovery, and canonical verify.
- forbidden_bypass: no default web, no production internet provider claim, no high-risk/external side-effect execution.
- user_visible_effect: generated runtime can support explicit research-agent web capability with citations under fixture provider.

## Check/Contrast/Fix Loop Evidence

- check: PASS. Required web tests, runtime/tool regressions, benchmark commands, full discover, repo checks, and canonical verify all passed.
- contrast: Phase 8 treats web-like tools as unsupported/external-blocked and has no source/citation output contract.
- fix: add explicit manifest-only web adapters and fixture provider while preserving all Phase 7/8 safety boundaries.

## Completion Criteria Evidence

- connected + accumulated + consumed.
- connected: manifest web tool declarations now flow through generated registry, policy, executor, ToolResult, audit, state, docs, and benchmark fixtures.
- accumulated: `runtime_state.json` records web ToolResult rows; `audit/events.jsonl` records query/url/source details; benchmark reports record `research_agent_web`.
- consumed: runtime benchmark consumes the research fixture with `CTCP_AGENT_WEB_PROVIDER=fixture`, and non-research cases assert no web access.

## Issue Memory Decision Evidence

- issue memory decision evidence: no persistent issue-memory update needed; first verify failure was a local import-path mismatch and is documented in `meta/reports/LAST.md`.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: Phase 9 requires queue binding, scoped implementation, verification, and auditable report evidence.
- skillized: no.
- reason: this changes generated runtime behavior and tests, not reusable Codex operator workflow.
