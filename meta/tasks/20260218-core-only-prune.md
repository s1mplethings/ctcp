# Task — core-only-prune

## Context
- User requested deeper removal of non-essential features.
- Keep only core runtime path for Qt GUI graph viewing and file preview.

## Acceptance (must be checkable)
- [x] Patch applies cleanly (`git apply ...`).
- [x] Remove AI Doc generator feature chain (UI action + bridge API + scripts/templates).
- [x] Remove self-check/self-improve feature chain.
- [x] Remove stale recipe chain not needed for runtime.
- [x] `scripts/verify_repo.ps1` passes with explicit output.

## Plan
1) Record selection in `meta/externals/core-only-prune.md`.
2) Remove non-core feature chains and stale references.
3) Run verify gate.
4) Record results and residual risks.

## Notes / Decisions
- This patch intentionally prunes optional tooling, not core runtime graph rendering.

## Results
- Removed AI Doc generator chain:
  - `MainWindow` menu action removed.
  - `SddaiBridge::generateAidoc` and template copy helper removed.
  - removed `scripts/gen_aidoc.ps1`, `scripts/gen_aidoc.sh`.
  - removed `ai_context/ai_context/templates/aidoc/*`.
- Removed self-check/self-improve chain:
  - removed `scripts/self_check.py`, `scripts/self_improve.py`, `scripts/_issue_memory.py`.
  - removed `docs/SELF_CHECK_SYSTEM.md`.
  - removed tracked artifacts under `runs/self_check/*`.
  - removed `issue_memory/*`.
- Removed stale recipe chain:
  - removed `ai/RECIPES/qtweb-graph-force/*`.
  - updated `ai/RECIPES/recipe_index.json`.
  - updated `ai/DETECTORS/rules.json` to avoid stale suggestions.
- Verify (pass): `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - `cmake` not found -> C++ build skipped
  - `web/package.json` missing -> web build skipped
  - `redundancy_guard` passed
