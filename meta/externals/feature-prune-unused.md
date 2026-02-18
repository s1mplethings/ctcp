# Externals Review — feature-prune-unused

## Goal
- Establish a practical method to identify and remove unused features/files with low regression risk.

## Constraints
- Offline only?: No (research online), but pruning must be verifiable locally.
- License constraints?: Prefer permissive licenses.
- Must support Windows?: Yes.
- Must be vendorable?: Prefer no new heavy dependency.

## Candidates
### A) vulture
- Link: https://github.com/jendrikseipp/vulture
- License: MIT
- Activity (last commit / releases): pushed 2025-11-25; latest release `v2.14` (2024-12-08).
- Bundle size / deps: repo size about 0.7 MB.
- Integration plan (exact files / APIs): run `vulture .` for Python dead code hints.
- Pros: lightweight, focused dead-code detector.
- Cons: Python-centric; cannot cover Qt/C++ and web assets fully.
- Decision: reject for mandatory gate; keep as optional helper.

### B) knip
- Link: https://github.com/webpro-nl/knip
- License: ISC
- Activity (last commit / releases): pushed 2026-02-17; latest release `knip@5.83.1` (2026-02-06).
- Bundle size / deps: repo size about 28 MB.
- Integration plan (exact files / APIs): run on web workspace for unused JS/TS files.
- Pros: strong JS/TS unused-file analysis.
- Cons: repo web side is plain static JS; introducing Node toolchain for this is heavy.
- Decision: reject for now.

### C) depcheck
- Link: https://github.com/depcheck/depcheck
- License: MIT
- Activity (last commit / releases): pushed 2025-02-27; latest release `v1.4.7` (2023-10-17).
- Bundle size / deps: repo size about 2.0 MB.
- Integration plan (exact files / APIs): dependency hygiene for Node projects.
- Pros: easy dependency drift scan.
- Cons: no `web/package.json` in this repo; little value right now.
- Decision: reject (not applicable).

### D) include-what-you-use
- Link: https://github.com/include-what-you-use/include-what-you-use
- License: `NOASSERTION` on GitHub metadata
- Activity (last commit / releases): pushed 2026-02-10; latest release `0.25` (2025-09-20).
- Bundle size / deps: repo size about 5.8 MB.
- Integration plan (exact files / APIs): integrate into C++ compile tooling.
- Pros: helps C++ include-level cleanup.
- Cons: scope is includes, not feature/file-level pruning; setup overhead.
- Decision: reject for this task.

### E) clang-tidy (via llvm-project)
- Link: https://github.com/llvm/llvm-project
- License: `NOASSERTION` on GitHub metadata
- Activity (last commit / releases): pushed 2026-02-17; latest release tag `llvmorg-21.1.8` (2025-12-16).
- Bundle size / deps: very large monorepo.
- Integration plan (exact files / APIs): static checks in CMake pipeline.
- Pros: broad C++ static analysis.
- Cons: too heavy for immediate repo pruning patch.
- Decision: reject for now.

## Final pick
- Chosen: repository-local reference analysis (`rg` + entrypoint scanning + QRC resource graph) and direct removal of unreferenced/deprecated feature folders.
- Why: no new dependency, covers actual runtime wiring in this QtWebEngine app, and keeps patch minimal.
- What code to copy / what API to call:
  - Use `rg` to trace references from `src/`, `resources/app.qrc`, docs, scripts.
  - Remove assets not reachable from runtime resource graph.
  - Keep verify gate on `scripts/verify_repo.*`.

## Evidence
- Source: GitHub REST API `repos/<owner>/<repo>` and `releases/latest` fetched on 2026-02-17.
