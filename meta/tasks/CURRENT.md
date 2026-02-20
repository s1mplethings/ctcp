# Task - adlc-self-improve-core-loop

## Queue Binding
- Queue Item: `N/A (user-directed hotfix task)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- Implement one minimal, runnable self-improve core loop workflow:
  `doc -> analysis -> find(local librarian) -> plan -> build -> verify -> contrast -> fix(loop) -> stop`
- Keep all existing quality gates enabled and passing.

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: workflow and evidence artifacts are explicit and auditable
- [x] DoD-2: quality gates remain enabled (no bypass)
- [x] DoD-3: cross-platform scripts and tests pass in repo gate

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local implementation)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first
   - add `docs/PATCH_CONTRACT.md`
   - update workflow registry spec artifacts
2) Implement core modules
   - add run state/local librarian/contract guard/contrast rules tools
3) Implement workflow + dispatch wiring
   - add `scripts/workflows/adlc_self_improve_core.py`
   - register in `workflow_registry/index.json`
   - add workflow dispatch entry script
4) Verify and report
   - run unit tests + `scripts/verify_repo.*`
   - update `meta/reports/LAST.md` with command evidence

## Notes / Decisions
- No new third-party dependency; Python stdlib only.
- `rg` is optional accelerator; pure Python fallback required.

## Results
- Added core modules:
  - `tools/run_state.py`
  - `tools/local_librarian.py`
  - `tools/contract_guard.py`
  - `tools/contrast_rules.py`
- Added workflow and dispatch integration:
  - `scripts/workflows/adlc_self_improve_core.py`
  - `scripts/workflow_dispatch.py`
  - `workflow_registry/adlc_self_improve_core/recipe.yaml`
  - `workflow_registry/index.json` registration
- Added contract and patch protocol docs:
  - `contracts/allowed_changes.yaml`
  - `docs/PATCH_CONTRACT.md`
- Added unit tests and verify integration:
  - `tests/test_local_librarian.py`
  - `tests/test_contract_guard.py`
  - `tests/test_contrast_rules.py`
  - `tests/test_workflow_dispatch.py`
  - `tests/test_suite_gate.py`
  - `tools/checks/suite_gate.py` supports scalar `required_env` and clearer network-block reasons
  - `scripts/verify_repo.ps1` / `scripts/verify_repo.sh` now run unittest discover
- Validation passed:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - `bash scripts/verify_repo.sh`
