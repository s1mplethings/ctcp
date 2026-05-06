# Task Archive - Source Stage Boundary Refactor

- Queue Item: `ADHOC-20260506-source-stage-boundary-refactor`
- Date: `2026-05-06`
- Lane: Delivery Lane
- Status: `done`

## Scope

Behavior-preserving source-stage refactor:

- extract provider-authored source-file parsing/materialization from `project_generation_source_stage.py`
- extract high-quality extended evidence materialization from `project_generation_source_stage.py`
- keep `normalize_source_generation_stage()` orchestration and report semantics stable

## Results

- `tools/providers/project_generation_provider_source_files.py` added.
- `tools/providers/project_generation_extended_evidence.py` added.
- `tools/providers/project_generation_source_stage.py` reduced from `995` lines to `648`.
- Existing private helper import compatibility was preserved for tests.

## Verification

- `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_source_stage.py tools\providers\project_generation_provider_source_files.py tools\providers\project_generation_extended_evidence.py` -> exit 0
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0
- `.venv\Scripts\python.exe scripts\plan_check.py` -> exit 0
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0

## Skill Decision

- skillized: no, because this is a one-off source-stage boundary refactor using existing `ctcp-workflow`.
