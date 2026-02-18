# Task — redundancy-cleanup

## Context
- Repository root currently contains temporary/debug leftovers that are not part of product logic.
- This creates noise, increases patch entropy, and makes packaging/verification less predictable.

## Acceptance (must be checkable)
- [x] Patch applies cleanly (`git apply ...`).
- [x] Remove confirmed redundant files: `_tmp_patch.py`, `patch_debug.txt`, `1.1.0.txt`.
- [x] Add a repository-level anti-redundancy guard and wire it into `scripts/verify_repo.ps1` and `scripts/verify_repo.sh`.
- [x] Add explicit guidance for adding files without creating redundancy.
- [x] `scripts/verify_repo.*` runs and outputs key pass/fail signals.

## Plan
1) Research-first: write `meta/externals/redundancy-cleanup.md`.
2) Implement cleanup + prevention guard.
3) Verify using `scripts/verify_repo.*`.
4) Document results and any follow-up.

## Notes / Decisions
- Keep this patch single-theme: remove high-confidence redundant files only.
- Do not perform broad archive/history pruning in this patch to avoid unintended regressions.
- Prefer local script enforcement over heavyweight new dependencies.

## Results
- Completed external comparison and selected local guard approach.
- Deleted redundant temp/debug files from repo root.
- Added `tools/checks/redundancy_guard.py` and integrated it into verify gate.
- Added `docs/21_redundancy_guardrails.md` for future file-add discipline.
- Verify run (pass): `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - `cmake` not found -> C++ build skipped
  - `web/package.json` missing -> web build skipped
  - redundancy guard passed
- Verify run (failed in current Windows shell): `bash scripts/verify_repo.sh`
  - failed with `set: pipefail\r: invalid option name` (CRLF/WSL line-ending execution issue)
