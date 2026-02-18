# Externals Review — core-only-prune

## Goal
- Keep only core runtime functionality (Qt GUI + graph view), prune optional AI scaffolding and self-improvement tooling.

## Constraints
- Offline only?: No (research online), but pruning must be validated locally.
- License constraints?: Prefer permissive tooling if needed.
- Must support Windows?: Yes.
- Must be vendorable?: No new dependency preferred.

## Candidates
### A) vulture
- Link: https://github.com/jendrikseipp/vulture
- License: MIT
- Activity (last commit / releases): pushed 2025-11-25; latest release `v2.14` (2024-12-08).
- Bundle size / deps: ~0.7 MB.
- Integration plan (exact files / APIs): optional Python dead-code scan.
- Pros: lightweight.
- Cons: Python only; cannot verify Qt/web reachability.
- Decision: reject as mandatory, keep as optional.

### B) knip
- Link: https://github.com/webpro-nl/knip
- License: ISC
- Activity (last commit / releases): pushed 2026-02-17; latest release `knip@5.83.1` (2026-02-06).
- Bundle size / deps: ~28 MB.
- Integration plan (exact files / APIs): optional JS unused-file scan.
- Pros: strong JS analysis.
- Cons: too heavy for current plain-static web assets.
- Decision: reject.

### C) depcheck
- Link: https://github.com/depcheck/depcheck
- License: MIT
- Activity (last commit / releases): pushed 2025-02-27; latest release `v1.4.7` (2023-10-17).
- Bundle size / deps: ~2 MB.
- Integration plan (exact files / APIs): Node dependency hygiene.
- Pros: simple package cleanup.
- Cons: no `web/package.json` in this repo.
- Decision: reject.

### D) include-what-you-use
- Link: https://github.com/include-what-you-use/include-what-you-use
- License: `NOASSERTION` in GitHub metadata
- Activity (last commit / releases): pushed 2026-02-10; latest release `0.25` (2025-09-20).
- Bundle size / deps: ~5.8 MB.
- Integration plan (exact files / APIs): C++ include hygiene.
- Pros: useful for C++ include quality.
- Cons: not focused on feature-level pruning.
- Decision: reject.

### E) Manual reachability audit
- Link: repository-local method (`rg` + CMake entrypoint + QRC entrypoint graph)
- License: N/A
- Activity: immediate and repo-specific
- Bundle size / deps: zero additional dependencies
- Integration plan (exact files / APIs): trace runtime path from `src/main.cpp` + `MainWindow.cpp` + `resources/app.qrc`, then remove unreferenced optional chains.
- Pros: highest confidence for this repo's architecture.
- Cons: requires careful manual review.
- Decision: use.

## Final pick
- Chosen: manual reachability audit + targeted deletion + verify.
- Why: best fit for mixed C++/Qt/web repo, no dependency overhead.
- What code to copy / what API to call:
  - `rg` for references.
  - remove optional chains: aidoc generation, self_check loop, stale recipe chain.
  - validate with `scripts/verify_repo.ps1`.

## Evidence
- GitHub API metadata fetched on 2026-02-17 for candidate tools.
