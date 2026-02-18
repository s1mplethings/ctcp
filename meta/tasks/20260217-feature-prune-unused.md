# Task — feature-prune-unused

## Context
- User requests a full pass to remove unnecessary features and keep only needed runtime capability.
- Current repo contains historical/compatibility web feature folders that are not used by the active runtime entry.

## Acceptance (must be checkable)
- [x] Patch applies cleanly (`git apply ...`).
- [x] Remove unneeded web feature folders that are not used by runtime path.
- [x] Remove stale references from resource packaging and recipe index.
- [x] `scripts/verify_repo.ps1` runs with explicit pass/fail output.

## Plan
1) Research-first record in `meta/externals/feature-prune-unused.md`.
2) Remove high-confidence unused feature directories and references.
3) Verify with `scripts/verify_repo.ps1`.
4) Record results.

## Notes / Decisions
- Scope in this patch: only high-confidence unused/deprecated features.
- Do not remove active graph_spider implementation or project scanner behavior.

## Results
- Removed unused/deprecated web feature folders:
  - `web/_archive/*`
  - `web/graph_force/*`
  - `web/graph_spider_v2/*`
- Cleaned resource packaging: removed redirect-shell entries from `resources/app.qrc`.
- Cleaned stale AI recipe references:
  - `ai/RECIPES/recipe_index.json` removed non-existent recipe paths.
  - `ai/DETECTORS/rules.json` removed detectors that suggested removed recipe IDs.
- Verify: pending.
- Verify (pass): `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - `cmake` not found -> C++ build skipped
  - `web/package.json` missing -> web build skipped
  - `redundancy_guard` passed
