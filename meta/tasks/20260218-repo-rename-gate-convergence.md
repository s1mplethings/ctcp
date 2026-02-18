# Task — repo-rename-gate-convergence

## Context
- Repo has been renamed to `ctcp`, but build/docs/scripts still contain old identifiers and broken instructions.
- Current state can cause immediate operator failure (missing `build_v6.cmd`, dead patch apply command, duplicate verify entry confusion).

## Acceptance (must be checkable)
- [x] Patch applies cleanly (`git apply ...`).
- [x] Build docs and CMake naming converge to `ctcp`.
- [x] `README.md` quick start no longer points to broken/nonexistent flow.
- [x] `PATCH_README.md` no longer references a missing patch file.
- [x] `scripts/verify.*` works as a single public gate and is no longer placeholder-only.
- [x] AIDoc template resolution works with current template layout and external project roots.
- [x] `scripts/verify_repo.ps1` passes (or clear fail reason recorded).

## Plan
1) Research-first comparison in `meta/externals/repo-rename-gate-convergence.md`.
2) Fix naming drift in CMake/build/docs/verify artifacts.
3) Converge verify entrypoint by delegating `scripts/verify.*` to `scripts/verify_repo.*`.
4) Fix AIDoc template path resolution in CLI scripts and GUI bridge.
5) Run verify gate and record results.

## Notes / Decisions
- Keep changes minimal and avoid broad refactors.
- Preserve existing `scripts/verify_repo.*` because AGENTS contract references it.
- Use `scripts/verify.*` as user-facing entrypoint to remove ambiguity.

## Results
- Naming convergence:
  - `CMakeLists.txt`: project id changed to `ctcp`.
  - `BUILD.md`: repo-root command and executable name changed to `ctcp`.
  - `scripts/verify_repo.ps1`: executable lookup changed to `ctcp.exe`.
- Broken-entrypoint fixes:
  - added missing `build_v6.cmd`.
  - `PATCH_README.md` rewritten to remove dead patch reference and point to existing patch file.
- Verify gate convergence:
  - `scripts/verify.ps1` and `scripts/verify.sh` now delegate to `scripts/verify_repo.*` and then run contract/doc-link checks.
  - placeholder-only behavior removed.
  - normalized shell scripts to LF (`scripts/verify.sh`, `scripts/verify_repo.sh`, `scripts/gen_aidoc.sh`) to avoid WSL/bash CRLF failures.
- AIDoc template stability:
  - `scripts/gen_aidoc.ps1` and `scripts/gen_aidoc.sh` now support both:
    - `ai_context/ai_context/templates/aidoc` (current layout)
    - `ai_context/templates/aidoc` (legacy compatibility)
  - `src/sddai_bridge.cpp` now resolves template directory from app/repo candidates first, and only then falls back to opened project root.
- Repo hygiene:
  - removed temporary root files `_tmp_patch.py` and `patch_debug.txt`.
- Verify outputs:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => PASS
  - `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` => PASS
  - `bash scripts/verify.sh` => PASS
