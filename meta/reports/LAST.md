# Demo Report - LAST

## Goal
- Land a minimal ADLC + multi-agent + local Local Librarian self-improve core loop:
  `doc -> analysis -> find -> plan -> build -> verify -> contrast -> fix(loop) -> stop`
- Register the workflow in registry/dispatch and keep `verify_repo` (PowerShell + shell) passing.

## Readlist
- `ai_context/00_AI_CONTRACT.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/00_CORE.md`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- `scripts/resolve_workflow.py`
- `scripts/ctcp_dispatch.py`
- `scripts/ctcp_orchestrate.py`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/TEMPLATE_LAST.md`

## Plan
1. Docs/Spec first:
   - add patch protocol contract doc
   - update doc index generator and README index
2. Implement core modules:
   - run state persistence
   - deterministic local librarian
   - contract guard
   - verify contrast rule classifier
3. Implement workflow and dispatch wiring:
   - add `adlc_self_improve_core` workflow script
   - register workflow recipe/index
   - add workflow dispatch entry
4. Add tests and integrate into verify_repo:
   - unittest suite for librarian/guard/contrast/dispatch
   - run via `python -m unittest discover -s tests -p "test_*.py"`
5. Validate:
   - run PowerShell verify gate
   - run bash verify gate

## Timeline / Trace Pointer
- Run pointer file: `meta/run_pointers/LAST_RUN.txt`
- verify_repo.ps1 lite replay run:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260220-000103`
- verify_repo.sh lite replay run:
  - `/home/sunom/.local/share/ctcp/runs/ctcp/simlab_runs/20260219-235615`

## Changes
- Added:
  - `contracts/allowed_changes.yaml`
  - `docs/PATCH_CONTRACT.md`
  - `tools/run_state.py`
  - `tools/local_librarian.py`
  - `tools/contract_guard.py`
  - `tools/contrast_rules.py`
  - `scripts/workflow_dispatch.py`
  - `scripts/workflows/adlc_self_improve_core.py`
  - `workflow_registry/adlc_self_improve_core/recipe.yaml`
  - `tests/test_local_librarian.py`
  - `tests/test_contract_guard.py`
  - `tests/test_contrast_rules.py`
  - `tests/test_workflow_dispatch.py`
  - `tests/test_suite_gate.py`
- Updated:
  - `tools/checks/suite_gate.py` (support scalar `required_env`, clearer network-block reason, explicit `suite_file` in evaluator output)
  - `workflow_registry/index.json` (register new workflow)
  - `scripts/verify_repo.ps1` (run unittest discover)
  - `scripts/verify_repo.sh` (run unittest discover + python shim for shell envs with python3 only)
  - `scripts/sync_doc_links.py` (include patch contract doc)
  - `README.md` (doc index sync)
  - `meta/tasks/CURRENT.md`

## Verify
- `python -m unittest discover -s tests -p "test_*.py"`
  - `Ran 14 tests ... OK`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - `[verify_repo] OK`
  - lite replay: `passed=8 failed=0`
  - unittest discover executed and passed
- `bash scripts/verify_repo.sh`
  - `[verify_repo] OK`
  - lite replay: `passed=8 failed=0`
  - unittest discover executed and passed

## Open Questions
- None.

## Next Steps
1. Add a focused simlab scenario for `adlc_self_improve_core` workflow state-resume behavior.
2. Expand contrast rules with per-gate regex diagnostics once more failure corpora are collected.
