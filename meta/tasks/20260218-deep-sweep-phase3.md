# Task — deep-sweep-phase3

## Context
- Third cleanup pass requested by user to further remove non-essential functionality.
- Current repo still has dual verify entrypoints and non-runtime AI apply recipe chain.

## Acceptance (must be checkable)
- [x] Patch applies cleanly (`git apply ...`).
- [x] Consolidate verification semantics to `scripts/verify_repo.*` only.
- [x] Remove non-runtime `ai/` + `scripts/ai_apply` feature chain.
- [x] Remove stale references in docs/spec/scanner logic.
- [x] `scripts/verify_repo.ps1` passes.

## Plan
1) Record selection in `meta/externals/deep-sweep-phase3.md`.
2) Remove legacy verify placeholders and retarget scanner/docs/spec.
3) Remove AI apply/recipe chain and cleanup references.
4) Run verify gate and record result.

## Notes / Decisions
- Keep runtime Qt GUI + graph + bridge functionality untouched.
- Keep user-provided untracked fixture/suite files untouched.

## Results
- Updated project detection logic and spec to look for `verify_repo.ps1` / `verify_repo.sh`.
- Removed placeholder `scripts/verify.ps1` and `scripts/verify.sh`.
- Updated docs to point to `scripts/verify_repo.*`:
  - `docs/00_overview.md`
  - `docs/03_quality_gates.md`
  - `docs/04_project_detection.md`
  - `docs/10_workflow.md`
- Removed non-runtime AI apply chain:
  - deleted `ai/**`
  - deleted `scripts/ai_apply/**`
- Verify (pass): `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - cmake not found -> C++ build skipped
  - web/package.json missing -> web build skipped
  - redundancy guard passed
