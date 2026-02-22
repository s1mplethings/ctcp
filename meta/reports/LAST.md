# Demo Report - LAST

## Goal
- Upgrade CTCP provider loop from mostly `manual_outbox` to core auto providers:
  - `contract_guardian` via `local_exec`
  - `patchmaker` + `fixer` via `api_agent`
- Keep researcher offline/manual behavior.
- Ensure tests are enforced by `scripts/verify_repo.*`.

## Readlist
- `ai_context/00_AI_CONTRACT.md` (minimal change contract)
- `README.md` (workflow + verify entrypoints)
- `BUILD.md` (headless build assumptions)
- `PATCH_README.md` (patch delivery baseline)
- `TREE.md` (repo layout orientation)
- `docs/03_quality_gates.md` (verify_repo gate expectations)
- `ai_context/problem_registry.md` (evidence-first failures)
- `ai_context/decision_log.md` (deviation log baseline)
- `scripts/ctcp_dispatch.py` (provider dispatch + gate mapping)
- `tools/providers/manual_outbox.py` (manual provider baseline)
- `tools/providers/local_exec.py` (existing local provider)
- `workflow_registry/adlc_self_improve_core/recipe.yaml` (workflow defaults)
- `scripts/workflows/adlc_self_improve_core.py` (self-improve round artifacts)
- `scripts/verify_repo.ps1` / `scripts/verify_repo.sh` (gate commands)
- `tools/contract_guard.py` / `tools/local_librarian.py` / `tools/contrast_rules.py` (guardian/evidence helpers)
- `tests/test_self_improve_external_requirements.py`
- `tests/test_openai_external_api_wrappers.py`
- `tests/test_workflow_dispatch.py`

## Plan
1. Docs/Spec first: recipe and dispatcher provider contracts updated.
2. Code: add `api_agent`, extend `local_exec`, wire dispatch provider selection/recipe defaults.
3. Verify: run full unittest and both verify_repo scripts.
4. Report: update task + LAST report.

## Timeline / Trace
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- External run folder: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe`
- External trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe\TRACE.md`

## Changes
- Added:
  - `tools/providers/api_agent.py`
  - `tests/test_provider_selection.py`
  - `tests/test_providers_e2e.py`
- Updated:
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/local_exec.py`
  - `workflow_registry/adlc_self_improve_core/recipe.yaml`
  - `specs/modules/dispatcher_providers.md`
  - `docs/30_artifact_contracts.md`
  - `meta/tasks/CURRENT.md`

## Verify
- `python -m unittest discover -s tests -p "test_*.py"`
  - PASS (`Ran 36 tests ... OK`)
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1`
  - PASS (cmake configure/build, ctest lite, workflow checks, contract checks, doc index check, simlab lite replay, unittest all green)
- `bash scripts/verify_repo.sh`
  - PASS (workflow checks, contract checks, doc index check, simlab lite replay, unittest all green)

## Questions (only if blocking)
- None.

## Next steps
- None.
