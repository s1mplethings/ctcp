# Demo Report - Source Stage Boundary Refactor

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/decision_log.md`
- `tools/providers/project_generation_source_stage.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_api_agent_templates.py`

### Plan
1. Bind `ADHOC-20260506-source-stage-boundary-refactor`.
2. Extract provider-authored source-file parsing/materialization into a helper module.
3. Extract high-quality extended evidence materialization into a helper module.
4. Preserve the source-stage orchestration entrypoint and compatibility imports.
5. Run focused source-generation tests, code-health checks, and canonical verify.

### Changes
- `tools/providers/project_generation_provider_source_files.py`
  - New module for provider-authored `path/content` row extraction, safe materialization under `project_root`, source-map updates, and package marker completion.
- `tools/providers/project_generation_extended_evidence.py`
  - New module for high-quality team-task and indie-studio extended evidence screenshots/docs/ledger materialization.
- `tools/providers/project_generation_source_stage.py`
  - Removed the extracted helper bodies.
  - Kept `normalize_source_generation_stage()` orchestration intact.
  - Re-exported the provider helper needed by existing tests.
- task/report metadata updated for this refactor.

### Verify
- Passed:
  - `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_source_stage.py tools\providers\project_generation_provider_source_files.py tools\providers\project_generation_extended_evidence.py` -> exit 0.
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0.
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- Passed:
  - `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
  - `.venv\Scripts\python.exe scripts\plan_check.py` -> exit 0.
  - `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
  - `git diff --check` -> exit 0, CRLF warnings only.
  - `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.
- Canonical verify summary:
  - profile: `code`
  - ownership: `task-owned`
  - lite replay: `15 passed / 0 failed`
  - python unit tests: `517 tests OK, 4 skipped`
  - result: `OK`
- first failure point evidence:
  - Initial focused artifact test failed because the command lacked `PYTHONPATH`; rerun with `PYTHONPATH=(Get-Location).Path` passed.
  - After extraction, an existing test still imported `_ensure_provider_package_init_files` from the old module; compatibility re-export fixed it.
- minimal fix strategy evidence:
  - Keep private helper compatibility while moving implementation into the new provider-source module.
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was executed by canonical verify and passed.
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was executed by canonical verify and passed.
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was executed by canonical verify and passed.

### Questions
- None.

### Demo
- `project_generation_source_stage.py` line count reduced from `995` to `648`.
- New helper modules:
  - `project_generation_provider_source_files.py`: `128` lines.
  - `project_generation_extended_evidence.py`: `244` lines.

### Integration Proof
- connected: source stage imports the extracted helper modules.
- accumulated: focused test and code-health evidence is recorded here.
- consumed: source-generation tests consume the refactored helper path and pass.

### Skill Decision
- skillized: no, because this is a one-off source-stage boundary refactor using existing `ctcp-workflow`.
