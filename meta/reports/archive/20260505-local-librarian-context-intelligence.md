# Demo Report - Local Librarian Context Intelligence

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
- `llm_core/retrieval/repo_search.py`
- `tests/test_local_librarian.py`

## Plan
1. Bind a separate Delivery Lane task for local librarian context intelligence.
2. Keep the librarian local and deterministic; do not add project-specific templates or API calls.
3. Let sparse `file_request.json` inputs trigger budgeted repo search from goal/reason/requested-path tokens.
4. Record context selection evidence inside `context_pack.json`.
5. Add focused regression coverage and run repo checks.

## Changes
- `tools/librarian_context_pack.py`
  - Added request-derived query extraction.
  - Added budgeted inferred local repo context snippets.
  - Added `selection_strategy` evidence to context packs.
  - Preserved mandatory files, explicit needs, deny-prefix rules, and budget behavior.
- `tests/test_local_librarian.py`
  - Added sparse-request regression for inferred local context.
- `meta/tasks/CURRENT.md`, `meta/tasks/ARCHIVE_INDEX.md`
  - Bound and closed the scoped task.

## Verify
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_local_librarian.py" -v` -> exit 0, 8 tests OK.
- `.venv\Scripts\python.exe -m py_compile tools\librarian_context_pack.py tests\test_local_librarian.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `git diff --check -- tools/librarian_context_pack.py tests/test_local_librarian.py meta/tasks/CURRENT.md` -> exit 0; only CRLF warnings.
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1` -> exit 1.
- First failure point: module protection check failed on pre-existing dirty files outside this task: `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, `tests/test_runtime_wiring_contract.py`.
- minimal fix strategy evidence: bind/finish those unrelated dirty files separately, then rerun canonical verify.
- triplet issue memory command evidence:
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was not rerun because issue-memory runtime code did not change.
  - issue_memory_decision: no new entry; this is a quality improvement, not a repeated observed defect.
- triplet skill consumption command evidence:
  - `.agents/skills/ctcp-workflow/SKILL.md` was consumed for this repo change.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was not rerun because runtime skill loading did not change.

## Questions
- None.

## Demo
- Sparse librarian requests can now receive relevant local snippets without asking API for more context.
- The behavior is auditable through `selection_strategy` and `why: inferred_context`.
- No concrete project template or CTCP-owned project standard was introduced.

## Integration Proof
- connected: existing `scripts/ctcp_librarian.py` entrypoint reaches `build_context_pack`.
- accumulated: inferred query/candidate/selection evidence is written into `context_pack.json`.
- consumed: downstream project-generation code already consumes `context_pack.files`; the regression proves inferred files enter that field.

## Skill Decision
- skillized: no, because this is an existing runtime component improvement rather than a reusable external workflow. Skillization would be premature unless future tasks repeatedly need a separate librarian tuning procedure.
