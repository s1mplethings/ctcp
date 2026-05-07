# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260507-agent-interaction-source-repair.md`
- Date: `2026-05-07`
- Topic: `Agent Interaction Source Repair`

### Readlist
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

### Plan
1. Bind `ADHOC-20260507-agent-interaction-source-repair`.
2. Strengthen source_generation prompt interaction so Builder, Integration QA, Product QA, and Delivery QA have explicit duties before returning files.
3. Translate previous runtime probe failures into actionable repair items for bare sibling imports, missing re-exports, constructor/API signature mismatches, and unreachable web endpoints.
4. Capture the recurring failure class in issue memory.
5. Run focused source-generation tests, workflow/code-health gates, and canonical verify.

### Changes
- `ctcp_adapters/source_generation_prompt.py`
  - Adds an explicit virtual-team handoff protocol for generated source delivery.
  - Requires Integration QA style checks for imports, package re-exports, and call signatures before the API returns JSON.
  - Forbids bare sibling imports such as `import service` / `import models` inside src-layout packages.
  - Requires entrypoint scripts to import concrete package modules/symbols that actually exist.
  - Requires an API signature matrix across model constructors, service methods, route handlers, exporter functions, and tests.
  - Requires detectable English README headings while allowing Chinese content under them.
  - Requires web/mobile-local projects to provide `/`, `/status`, and a command/action endpoint.
  - Converts previous runtime errors into targeted repair hints for dependency/import, re-export, constructor signature, and server reachability failures.
- `tests/test_api_agent_templates.py`
  - Locks the inter-agent source-generation handoff wording into prompt regressions.
  - Replays the live failure classes from the phone-to-PC voice-assistant generated project.
- `issue_memory/modifications.jsonl`
  - Records the recurring API-authored generated-project integration failure after the dependency fix.
- task metadata updated for this task.

### Verify
- Passed:
  - `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_api_agent_templates.py` -> exit 0.
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0 after report/current evidence updates.
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, ownership `task-owned`.
  - `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0 after keeping `tests/test_api_agent_templates.py` at 1000 lines.
  - `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.
- Canonical verify summary:
  - profile: `code`
  - ownership: `task-owned`
  - SimLab lite: `15 passed / 0 failed`
  - Python unit tests: `517 OK / 4 skipped`
  - result: `OK`
- First failure point evidence:
  - Initial `.venv\Scripts\python.exe scripts\workflow_checks.py` failed because `meta/reports/LAST.md` had not yet been updated for this patch.
  - Initial `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` failed because `tests/test_api_agent_templates.py` grew past the 1000-line guard.
- minimal fix strategy evidence:
  - Updated `meta/reports/LAST.md` for this task before rerunning workflow checks.
  - Added mandatory 10-step evidence sections to `meta/tasks/CURRENT.md`.
  - Compressed prompt-test assertions so `tests/test_api_agent_templates.py` stays at the 1000-line code-health threshold.
- triplet runtime wiring command evidence:
  - canonical verify executed `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` and passed 25 tests.
- triplet issue memory command evidence:
  - canonical verify executed `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` and passed 3 tests.
- triplet skill consumption command evidence:
  - canonical verify executed `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` and passed 3 tests.

### Questions
- None.

### Demo
- Concrete generated-project test from the rerun showed:
  - API source generation was connected and provider-authored.
  - syntax compilation passed.
  - CLI help, README serve, headless export, generated unittest, direct service construction, and HTTP/mobile endpoint checks failed.
  - key failures: `ModuleNotFoundError: No module named 'service'`, `CommandWhitelist.__init__()` missing `commands`, and unreachable `/status` / `/`.
- The next source_generation prompt now gives the API source agent a stricter QA handoff for those exact failures instead of only a generic validation failure.

### Integration Proof
- connected: `_render_prompt()` appends `render_source_generation_payload_requirements()` for `chair/source_generation`.
- accumulated: the live failure class is recorded in `issue_memory/modifications.jsonl`.
- consumed: focused prompt tests assert the new inter-agent protocol and live failure repair hints are present.

### Skill Decision
- skillized: no, because this is a local source-generation repair loop enhancement; it should become a skill only if the same inter-agent generated-source repair procedure stabilizes across multiple project domains.
