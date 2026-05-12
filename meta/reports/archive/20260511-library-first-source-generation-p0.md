# Demo Report - Library-first source_generation P0 foundation

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/04_execution_flow.md`
- `docs/12_virtual_team_contract.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- source_generation provider/runtime modules and focused tests

## Plan
1. Bind the new task and produce Virtual Team design artifacts.
2. Add provider payload normalization.
3. Add library-first source_generation artifacts and verification.
4. Default chunked source_generation to one-file batches.
5. Verify with focused tests and canonical gate.

## Changes
- Added `project_library_plan`, `file_manifest`, `file_task`, and `library_usage_verification` schema files.
- Added provider payload normalization for common source file payload shapes.
- Added library-first artifact generation and library usage verification.
- Connected library usage verification to source_generation pass/block logic.
- Updated chunked source_generation and prompt guidance toward file-manifested, library-first provider source.

## Verify
- PASS: py_compile for changed Python modules returned 0.
- PASS: `tests.test_project_generation_library_first` returned 0, 4 tests OK.
- PASS: `tests.test_api_source_chunking` returned 0, 2 tests OK.
- PASS: `discover -s tests -p "test_project_generation_provenance.py"` returned 0, 4 tests OK.
- PASS: `discover -s tests -p "test_project_generation_artifacts.py"` returned 0, 48 tests OK.
- PASS: `discover -s tests -p "test_api_agent_templates.py"` returned 0, 22 tests OK.
- PASS: workflow/module/patch/code-health focused gates returned 0.
- PASS: `verify_repo.ps1 -Profile code` with `CTCP_SKIP_LITE_REPLAY=1` returned 0; Python unit tests ran 541 tests with 4 skipped.
- triplet runtime wiring command evidence: `test_runtime_wiring_contract.py` passed inside canonical verify, 25 tests OK.
- triplet issue memory command evidence: `test_issue_memory_accumulation_contract.py` passed inside canonical verify, 3 tests OK.
- triplet skill consumption command evidence: `test_skill_consumption_contract.py` passed inside canonical verify, 3 tests OK.

## Questions
- None.

## Demo
- New source_generation reports expose library/file task artifacts and library usage verification.
- Provider payloads normalize to `provider_source_files` with `path` and `content`.
- Chunked source_generation defaults to one requested file per content batch.

## First Failure And Repair
- minimal fix strategy: keep this patch to P0/P1 source_generation infrastructure; defer full Librarian RAG and model-budget routing to separate queue items.

## Skill Decision
- skill used: `ctcp-workflow`.
- skillized: no, because this is runtime source_generation infrastructure rather than a reusable agent workflow.
- persona_lab_impact: none.
