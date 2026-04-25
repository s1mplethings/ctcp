# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-21`
- Topic: `Default mainline validation and freeze`
- Mode: `Delivery Lane verification/freeze`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/02_workflow.md`
- `docs/architecture/contracts/run_manifest_contract.md`
- `tests/integration/test_mainline_run_contract.py`

### Plan
1. Validate the existing default mainline read-only.
2. Stop without freezing if any validation item fails.
3. If validation passes, add a freeze contract, sha256 manifest, and freeze test.
4. Run focused E2E, freeze test, workflow checks, and canonical verify or isolated verify.

### Changes
- Read-only validation passed for `docs/02_workflow.md`, ADLC unified orchestration wording, `docs/architecture/contracts/run_manifest_contract.md`, runtime write points, and `tests/integration/test_mainline_run_contract.py`.
- Added `docs/architecture/contracts/default_mainline_freeze_contract.md`.
- Added `artifacts/mainline_freeze_manifest.json` with sha256 records for the protected mainline files.
- Added `tests/integration/test_mainline_freeze_manifest.py`, which recalculates sha256 for every protected file and fails with `protected mainline file changed: <path>` on drift.

### Verify
- first failure point evidence:
  - `python scripts/workflow_checks.py` initially failed because `CURRENT.md` lacked mandatory check/contrast/fix, completion criteria, issue memory, and explicit elevation signal evidence.
  - after that fix, `python scripts/workflow_checks.py` failed because this report lacked mandatory first-failure/minimal-fix/triplet evidence.
- minimal fix strategy evidence:
  - add only the missing task/report evidence fields; do not modify frozen mainline implementation.
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` is the repo-wide triplet guard for runtime wiring.
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` is the repo-wide issue-memory guard.
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` is the repo-wide skill-consumption guard.
- final command evidence:
  - read-only `Select-String` checks for default mainline docs, run_manifest fields, runtime update calls, and E2E assertions => pass
  - `python -m unittest discover -s tests/integration -p "test_mainline_run_contract.py" -v` => exit `0`
  - `python -m unittest discover -s tests/integration -p "test_mainline_freeze_manifest.py" -v` => exit `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => exit `0`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => exit `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => exit `0`
  - `python scripts/workflow_checks.py` => exit `0`
  - main workspace `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`, first failure `module protection check` from unrelated dirty-worktree files
  - isolated workspace `D:\.c_projects\cqa`, commit `50b1dca`, `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`

### Questions
- None.

### Demo
- The existing mainline E2E still proves same-run co-presence through `artifacts/run_manifest.json`.
- The new freeze test proves the protected mainline surface is now hash-locked by `artifacts/mainline_freeze_manifest.json`.
