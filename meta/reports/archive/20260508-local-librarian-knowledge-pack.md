# Report Archive - Local Librarian Knowledge-Pack Enrichment

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `meta/tasks/CURRENT.md`
- `tools/librarian_context_pack.py`
- `scripts/ctcp_librarian.py`
- `tools/local_librarian.py`
- `tests/test_local_librarian.py`
- `specs/ctcp_context_pack_v1.json`
- `specs/modules/librarian_context_pack.md`

## Plan

1. Bind `ADHOC-20260508-local-librarian-knowledge-pack`.
2. Add local-only context file classification and compact metadata.
3. Update context-pack schema/spec docs for optional metadata fields.
4. Add focused regression tests.
5. Run focused tests, code-health, workflow checks, and canonical verify.

## Changes

- Added local-only role classification for context-pack file rows.
- Added per-file `role_hint`, `relevance_summary`, `compression_hint`, `must_follow_rules`, and `avoid_patterns`.
- Added top-level `knowledge_summary` with boundary `evidence_only_not_task_assignment`.
- Documented optional metadata fields in `specs/ctcp_context_pack_v1.json`.
- Documented the librarian boundary in `specs/modules/librarian_context_pack.md`.
- Added regression coverage in `tests/test_local_librarian.py`.
- Added `specs` to `artifacts/PLAN.md` Scope-Allow for this schema/spec update.

## Verify

- `.venv\Scripts\python.exe -m py_compile tools\librarian_context_pack.py tests\test_local_librarian.py` -> exit 0.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_local_librarian.py" -v` -> exit 0, 9 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> exit 0, 25 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0, 520 Python tests OK with 4 skipped.

## Questions

- None.

## Demo

Local librarian output now carries compact API-consumption metadata while preserving the existing `path`/`why`/`content` contract. Downstream stages can read `role_hint`, `relevance_summary`, `must_follow_rules`, and `avoid_patterns` before deciding whether to send full local content to an API agent.

## First Failure And Repair

- first failure point evidence: workflow gate initially failed on missing task/report evidence.
- first failure point evidence: unskipped canonical verify failed at lite scenario replay due local runs-root permission and replay timeout in this environment.
- first failure point evidence: first skip-rerun failed because inherited `CTCP_FORCE_PROVIDER` forced mock-agent tests to use `api_agent`.
- minimal fix strategy evidence: add workflow evidence, align PLAN scope, use temp runs root, clear `CTCP_FORCE_PROVIDER`, skip the environment-stuck lite replay, then rerun canonical code-profile verify.

## Integration Proof

- connected: existing `scripts/ctcp_librarian.py` entrypoint reaches `build_context_pack`.
- accumulated: per-file metadata and `knowledge_summary` are written into `context_pack.json`.
- consumed: downstream planner/source-generation can consume the same `context_pack.files` while using metadata to reduce raw API context.

## Issue Memory

- issue memory decision: not required, because this is a proactive local-knowledge quality improvement rather than a repeated observed defect.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.

## Skill Decision

- skillized: no, because this extends an existing runtime component rather than creating a reusable external workflow.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
