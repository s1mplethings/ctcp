# Task Archive - Agent Interaction Source Repair

## Queue Binding

- Queue Item: `ADHOC-20260507-agent-interaction-source-repair`
- Layer/Priority: `L1 / P0`
- Status: `done`
- Lane: Delivery Lane
- Code changes allowed: yes

## Scope

Strengthen the source_generation retry interaction loop so validation failures from a provider-authored generated project are consumed as concrete Builder/Integration QA/Product QA/Delivery QA repair instructions by the next API source-generation attempt.

In scope:
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_api_agent_templates.py`
- `issue_memory/modifications.jsonl`
- repo task/report metadata

Out of scope:
- Telegram/support runtime behavior
- provider credentials/API endpoint selection
- editing external generated run output
- local deterministic generated-project templates

## Analysis

The live run `voice-assistant-phone-pc-smoke-20260507-rerun` proved that API source_generation was connected and provider-authored, but concrete generated-project tests still failed:

- `run_project_web.py --help` failed through package import before argparse.
- `src/readme/app.py` used bare sibling import `import service`, causing `ModuleNotFoundError: No module named 'service'`.
- A direct service workaround failed because `CommandWhitelist.__init__()` required `commands`.
- `/status` and `/` never became reachable because the server crashed before handling requests.

The previous dependency-focused fix improved the failure class from undeclared Flask imports to standard-library generated files, but raw validation evidence was still not specific enough as an agent-to-agent repair handoff.

## Changes

- Added explicit Builder/Integration QA/Product QA/Delivery QA handoff duties to the source-generation prompt.
- Required src-layout package modules to avoid bare sibling imports and use relative or package imports consistently.
- Required entrypoint scripts to import concrete package modules/symbols that actually exist.
- Required an API signature matrix for constructors, service methods, route handlers, exporter functions, and tests.
- Required detectable English README headings while allowing Chinese content under those headings.
- Required web/mobile-local projects to provide `/`, `/status`, and a command/action endpoint.
- Added previous-failure classifiers for:
  - dependency/import failures
  - bare sibling imports inside src-layout packages
  - missing imports/re-exports
  - constructor or method signature mismatches
  - unreachable local server endpoints
- Added focused prompt regression coverage for the live failure classes.
- Recorded the recurring failure class in issue memory.

## Verification

- `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_api_agent_templates.py` -> exit 0.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0 after report/current evidence updates.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, ownership `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.

Canonical verify summary:
- profile: `code`
- ownership: `task-owned`
- SimLab lite: `15 passed / 0 failed`
- Python unit tests: `517 OK / 4 skipped`
- result: `OK`

## Integration Proof

- connected: `_render_prompt()` appends `render_source_generation_payload_requirements()` for `chair/source_generation`.
- accumulated: `issue_memory/modifications.jsonl` records the generated-project integration failure class.
- consumed: prompt tests assert the new inter-agent handoff and live failure repair hints are present.

## Skill Decision

- skillized: no, because this is a local source-generation repair loop enhancement; it should become a skill only if the same inter-agent generated-source repair procedure stabilizes across multiple project domains.

## Closure

- Report: `meta/reports/archive/20260507-agent-interaction-source-repair.md`
- Queue status: `done`
