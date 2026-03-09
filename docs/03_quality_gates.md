# Quality Gates (DoD)

If this file conflicts with `docs/00_CORE.md`, `docs/00_CORE.md` wins.

## 1) Single DoD Entrypoint

Only these commands are valid acceptance gate entrypoints:

- Windows: `scripts/verify_repo.ps1`
- Unix: `scripts/verify_repo.sh`

No alternative `scripts/verify.*` family is authoritative for DoD in this repo.

## 2) Verify Evidence Naming (Unified Contract)

- Canonical machine verify artifact (run_dir): `artifacts/verify_report.json`.
- `proof.json` is removed from hard DoD contract; it is not required by `verify_repo.*`.
- `verify_report.md` may exist as optional human summary, but it is non-authoritative.
- Running `verify_repo.*` directly decides pass/fail by command exit code + logs.
  For repo-level tasks, command/evidence summary MUST be recorded in `meta/reports/LAST.md`.

## 3) Current `verify_repo.*` Gate Sequence (Script-Aligned)

`scripts/verify_repo.ps1` and `.sh` currently execute gates in this order:

1. Anti-pollution gate
   - Fail if tracked/unignored build outputs exist in repo (`build*/**`).
   - Fail if tracked/unignored run outputs exist in repo (`simlab/_runs*/**`, `meta/runs/**`).
2. Headless lite build path (if CMake exists)
   - Configure/build with `CTCP_ENABLE_GUI=OFF` and `BUILD_TESTING=ON`.
   - Run lite `ctest` selector when test files exist.
3. Workflow gate
   - Run `python scripts/workflow_checks.py`.
4. Plan/scope/behavior contract gates
   - `python scripts/plan_check.py`
   - `python scripts/patch_check.py`
   - `python scripts/behavior_catalog_check.py`
5. Contract and doc index gates
   - `python scripts/contract_checks.py`
   - `python scripts/sync_doc_links.py --check`
6. Triplet integration guard gate
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
7. Lite replay + Python unit tests
   - `python simlab/run.py --suite lite` (unless `CTCP_SKIP_LITE_REPLAY=1`)
   - `python -m unittest discover -s tests -p "test_*.py"`
8. Plan declared-gate/evidence replay check
   - `python scripts/plan_check.py --executed-gates <csv> --check-evidence`

Passing all required steps is a DoD pass.
First non-zero step is the first failure point for repair.

## 4) Optional Full Gate

- Enable via `--full` or `CTCP_FULL_GATE=1`.
- Windows runs `scripts/test_all.ps1` when present.
- Unix runs `scripts/test_all.sh` when present.
- Missing full test script is logged as skip, not silent pass.

## 5) Contract Update Rule

If a failure class is not covered by current gates:

1. Add the check to `scripts/verify_repo.ps1` and `.sh` (or shared gate script invoked by both).
2. Add/adjust tests or scenarios so the new gate is reproducible.
3. Update this document and `docs/30_artifact_contracts.md` in the same patch.
