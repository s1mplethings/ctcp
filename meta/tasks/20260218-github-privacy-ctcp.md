# Task — github-privacy-ctcp

## Context
- User requested two concrete outcomes:
  - private/local files should not be uploaded to GitHub;
  - public project name should be changed to `ctcp`.

## Acceptance (must be checkable)
- [x] Patch applies cleanly (`git apply ...`).
- [x] `.gitignore` blocks privacy-sensitive/local runtime artifacts.
- [x] Build-facing name is `ctcp` in core entrypoints (`CMakeLists.txt`, build doc, verify script).
- [x] `scripts/verify_repo.ps1` runs and result is recorded.

## Plan
1) Research-first writeup in `meta/externals/github-privacy-ctcp.md`.
2) Harden `.gitignore` for secrets/local artifacts.
3) Rename build-facing project name to `ctcp`.
4) Run verify gate and record result.

## Notes / Decisions
- Keep code changes minimal and avoid refactoring unrelated SDDAI domain wording.
- Do not touch unrelated dirty files already present in workspace.

## Results
- Updated privacy ignore patterns in `.gitignore`:
  - secret-like files (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.secret`, `*.secrets`, `*.credentials`)
  - env variants (`.env.*`, keep `.env.example`)
  - local Codex config (`/.codex/`)
  - local bundle runtime outputs (`/tests/fixtures/adlc_forge_full_bundle/runs/`, `/tests/fixtures/adlc_forge_full_bundle/fixtures/toy_py/.pytest_cache/`)
- Renamed build-facing project name to `ctcp`:
  - `CMakeLists.txt` project id
  - `BUILD.md` path and executable name
  - `README.md` title
  - `scripts/verify_repo.ps1` executable path variables
- Verify (pass): `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - `cmake` not found -> C++ build skipped
  - `web/package.json` missing -> web build skipped
  - redundancy guard passed
