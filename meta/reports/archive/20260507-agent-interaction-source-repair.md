# Report Archive - Agent Interaction Source Repair

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/decision_log.md`
- `ai_context/problem_registry.md`
- `ctcp_adapters/source_generation_prompt.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_source_helpers.py`
- `tools/providers/project_generation_validation.py`
- `tests/test_api_agent_templates.py`
- `tests/test_project_generation_artifacts.py`
- live run evidence: `%TEMP%\ctcp_runs\ctcp\voice-assistant-phone-pc-smoke-20260507-rerun`

## Plan

1. Bind `ADHOC-20260507-agent-interaction-source-repair`.
2. Strengthen source_generation prompt interaction so Builder, Integration QA, Product QA, and Delivery QA have explicit duties before returning files.
3. Translate previous runtime probe failures into actionable repair items for bare sibling imports, missing re-exports, constructor/API signature mismatches, and unreachable web endpoints.
4. Capture the recurring failure class in issue memory.
5. Run focused source-generation tests, workflow/code-health gates, and canonical verify.

## Changes

- `ctcp_adapters/source_generation_prompt.py`
  - Adds explicit virtual-team handoff duties.
  - Forbids bare sibling imports inside src-layout packages.
  - Requires entrypoint imports, package re-exports, signatures, routes, README commands, and tests to agree.
  - Adds targeted previous-failure repair hints.
- `tests/test_api_agent_templates.py`
  - Covers the inter-agent source-generation handoff and live failure classes.
- `issue_memory/modifications.jsonl`
  - Records the recurring generated-project integration failure.
- metadata updated and archived.

## Verify

- `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_api_agent_templates.py` -> exit 0.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0 after report/current evidence updates.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, ownership `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.

Canonical verify:
- profile: `code`
- ownership: `task-owned`
- SimLab lite: `15 passed / 0 failed`
- Python unit tests: `517 OK / 4 skipped`
- result: `OK`

First failure point:
- workflow check initially failed because `meta/reports/LAST.md` was not yet updated.
- code-health initially failed because `tests/test_api_agent_templates.py` exceeded the 1000-line growth guard.

Minimal fix strategy:
- updated report/current evidence,
- compressed test assertions back to 1000 lines,
- reran gates.

Triplet evidence:
- runtime wiring: 25 tests passed in canonical verify.
- issue memory: 3 tests passed in canonical verify.
- skill consumption: 3 tests passed in canonical verify.

## Questions

- None.

## Demo

The next API source-generation retry now receives the concrete QA handoff for the generated voice-assistant failure:

- replace bare sibling imports such as `import service`;
- align package `__init__` re-exports with real symbols;
- align constructors/method signatures such as `CommandWhitelist(commands)`;
- make web/mobile-local `/` and `/status` endpoints observable by validation;
- keep README headings detectable.

## Integration Proof

- connected: source-generation prompt renderer is reached from `chair/source_generation`.
- accumulated: issue memory records the recurring failure.
- consumed: focused tests assert the new handoff and repair hints.

## Skill Decision

- skillized: no, because this is a local source-generation repair loop enhancement; it should become a skill only if the same inter-agent generated-source repair procedure stabilizes across multiple project domains.
