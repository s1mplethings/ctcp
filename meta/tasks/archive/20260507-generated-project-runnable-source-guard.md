# Task Archive - Generated Project Runnable Source Guard

## Queue Binding

- Queue Item: `ADHOC-20260507-generated-project-runnable-source-guard`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Scope

- Lane: Delivery Lane.
- Purpose:
  - Generated projects must run under the current validation environment without relying on undeclared or uninstalled external packages.
  - Source-generation retries must receive exact README, runtime-probe, external-dependency, interface, and UX blocker feedback.
  - Provider-authored source remains required; local production templates remain forbidden.
- Allowed behavior change:
  - Source-generation API prompt constraints are stricter.
  - Previous-failure prompt feedback includes more blocker details.
- Forbidden:
  - no dependency installation bypass,
  - no validation relaxation,
  - no deterministic local production templates,
  - no Telegram/support runtime changes.

## Write Scope

- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_api_agent_templates.py`
- `issue_memory/modifications.jsonl`
- `artifacts/PLAN.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/ARCHIVE_INDEX.md`
- `meta/tasks/archive/20260507-generated-project-runnable-source-guard.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260507-generated-project-runnable-source-guard.md`

## Results

- Source-generation prompt now states that verifier probes do not run `pip install`, `poetry install`, `npm install`, or dependency bootstrap.
- Generated validation paths must use Python standard library or local generated code.
- Local HTTP/web projects are directed toward standard-library HTTP/HTML/JS instead of uninstalled Flask/FastAPI/Django-style dependencies.
- `--serve` and rich export probes must exit 0 under verifier probes instead of blocking forever.
- Previous-failure feedback now includes dependency errors, README missing sections/reasons, and UX blockers.
- The recurring API-authored generated-source validation failure was recorded in `issue_memory/modifications.jsonl`.

## Verification

- `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_api_agent_templates.py` -> exit 0.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, ownership `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `git diff --check` -> exit 0, CRLF warnings only.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.

## Closure

- canonical_verify: passed on 2026-05-07 with profile `code`.
- SimLab lite: `15 passed / 0 failed`.
- Python unit tests: `517 OK / 4 skipped`.
- Skill decision: skillized: no, because this is a bounded source-generation quality repair using existing `ctcp-workflow`.
- persona_lab_impact: none.
