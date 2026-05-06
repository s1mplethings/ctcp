# Demo Report - Chunked API Source Generation

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `meta/tasks/CURRENT.md`
- `llm_core/providers/api_provider.py`
- `llm_core/providers/api_source_chunking.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tools/providers/project_generation_source_stage.py`
- `tests/test_api_source_chunking.py`
- `tests/test_api_agent_templates.py`
- `tests/test_project_generation_artifacts.py`

## Plan
1. Split source-generation API output into manifest and file-content batches.
2. Merge provider-authored text locally.
3. Preserve existing source-stage validation.
4. Add focused tests and run gates.

## Changes
- Added `llm_core/providers/api_source_chunking.py`.
- Wired chunked source-generation from `llm_core/providers/api_provider.py`.
- Updated source-generation prompt instructions for manifest/batch phases.
- Added focused chunking tests.

## Verify
- Passed:
  - `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py llm_core\providers\api_source_chunking.py llm_core\providers\api_provider.py tools\providers\project_generation_source_stage.py tests\test_api_source_chunking.py tests\test_api_agent_templates.py tests\test_project_generation_artifacts.py`
  - `.venv\Scripts\python.exe tests\test_api_source_chunking.py -v`
  - `.venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v`
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k chunked_source_generation -v`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
- Failed:
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
  - first canonical verify failure: module protection rejected pre-existing out-of-scope dirty files `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, and `tests/test_runtime_wiring_contract.py`.
- first failure point evidence: prior long API calls failed before source output materialized; this patch reduces per-call output size.
- minimal fix strategy evidence: keep API text authorship, split output, merge locally, and validate normally.
- triplet runtime wiring command evidence: focused chunking test exercises `api_provider._run_agent_phase`; `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was not rerun because runtime bridge wiring did not change.
- triplet issue memory command evidence: existing issue memory remains the motivating failure; `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was not rerun.
- triplet skill consumption command evidence: `.agents/skills/ctcp-workflow/SKILL.md` was consumed; `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was not rerun.

## Questions
- None.

## Demo
- Source generation now uses manifest then file-content batches when the output contract freeze exists.

## Integration Proof
- connected: source-generation dispatch reaches chunking executor.
- accumulated: manifest/batch prompts and merged JSON are recorded.
- consumed: existing source-stage normalization consumes the merged provider source bundle.
