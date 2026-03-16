# Report Archive - 2026-03-15 - 薄主合同 + 单流程 + 局部覆盖的 agent 规则收口

## Readlist

- `AGENTS.md`
- `README.md`
- `docs/04_execution_flow.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/03_quality_gates.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`

## Plan

1. Rewrite root `AGENTS.md` into a thin main contract.
2. Reposition `README.md` and `docs/04_execution_flow.md`.
3. Align direct conflict docs and route local concerns to existing docs / skills.
4. Run workflow/contract/doc-index checks and contract-profile verify.

## Verify

- `python scripts/workflow_checks.py` => `1`, then `0` after adding triplet command references to `meta/reports/LAST.md`
- `python scripts/contract_checks.py` => `0`
- `python scripts/sync_doc_links.py --check` => `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` => `0`
- triplet command references retained in `meta/reports/LAST.md`:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
- final consistency recheck after report refresh => `workflow_checks=0`, `contract_checks=0`, `sync_doc_links --check=0`, `verify_repo(contract)=0`
