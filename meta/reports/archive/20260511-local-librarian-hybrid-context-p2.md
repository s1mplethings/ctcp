# Demo Report - Local Librarian hybrid context pack P2

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
- local librarian modules and tests

## Plan
1. Bind P2 local librarian task.
2. Add retrieval trace and librarian context pack contracts.
3. Add deterministic hybrid retrieval.
4. Extend context pack output and CLI artifact writes.
5. Verify focused and canonical gates.

## Changes
- Added schema contracts for `ctcp-librarian-context-pack-v1` and `ctcp-retrieval-trace-v1`.
- Added `tools/librarian_retrieval.py`.
- Extended `build_context_pack()` with `retrieval_trace`, `selected_context`, `constraints_for_downstream_agents`, and `missing_context`.
- Added `build_librarian_context_pack()`.
- Updated `scripts/ctcp_librarian.py` to write `artifacts/librarian_context_pack.json`.
- Added focused hybrid librarian tests.

## Verify
- PASS: py_compile for changed Librarian modules/tests returned 0.
- PASS: `tests.test_librarian_hybrid_context` returned 0, 3 tests OK.
- PASS: `discover -s tests -p "test_local_librarian.py"` returned 0, 9 tests OK.
- PASS: workflow/module/patch/code-health focused gates returned 0.
- PASS: `verify_repo.ps1 -Profile code` with `CTCP_SKIP_LITE_REPLAY=1` returned 0; Python unit tests ran 544 tests with 4 skipped.
- triplet runtime wiring command evidence: `test_runtime_wiring_contract.py` passed inside canonical verify, 25 tests OK.
- triplet issue memory command evidence: `test_issue_memory_accumulation_contract.py` passed inside canonical verify, 3 tests OK.
- triplet skill consumption command evidence: `test_skill_consumption_contract.py` passed inside canonical verify, 3 tests OK.

## Questions
- None.

## Demo
- Hybrid retrieval trace now records keyword and token-vector stages.
- Sparse requests can retrieve local CTCP docs, archived failure/report memory, and local library docs when present.
- Local Librarian writes both compatibility and richer context artifacts.

## First Failure And Repair
- first failure point evidence: legacy test expected `inferred_context` in selected file reason.
- repair: hybrid inferred reasons now preserve the marker.
- minimal fix strategy: keep this patch deterministic/local and defer persistent Ollama embeddings to a later scoped task.

## Skill Decision
- skill used: `ctcp-workflow`.
- skillized: no, because this extends runtime Librarian behavior rather than defining a reusable workflow.
- persona_lab_impact: none.
