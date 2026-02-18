# Externals Review — deep-sweep-phase3

## Goal
- Continue deep cleanup by removing non-runtime feature chains and consolidating verification entrypoints.

## Constraints
- Offline only?: No (research online), but execution must be local and deterministic.
- License constraints?: Prefer permissive licenses for optional tools.
- Must support Windows?: Yes.
- Must be vendorable?: Prefer no new dependencies.

## Candidates
### A) vulture
- Link: https://github.com/jendrikseipp/vulture
- License: MIT
- Activity (last commit / releases): pushed 2025-11-25; latest release `v2.14` (2024-12-08).
- Bundle size / deps: ~0.7 MB.
- Integration plan (exact files / APIs): optional `vulture .` for Python dead code.
- Pros: lightweight dead-code hints.
- Cons: Python only, not suitable for Qt/C++/QRC reachability.
- Decision: reject for mandatory gate.

### B) knip
- Link: https://github.com/webpro-nl/knip
- License: ISC
- Activity (last commit / releases): pushed 2026-02-17; latest release `knip@5.83.1` (2026-02-06).
- Bundle size / deps: ~28 MB.
- Integration plan (exact files / APIs): optional JS/TS unused scan.
- Pros: strong JS dependency and file usage checks.
- Cons: high overhead for this static-web + Qt repo.
- Decision: reject for this patch.

### C) depcheck
- Link: https://github.com/depcheck/depcheck
- License: MIT
- Activity (last commit / releases): pushed 2025-02-27; latest release `v1.4.7` (2023-10-17).
- Bundle size / deps: ~2.0 MB.
- Integration plan (exact files / APIs): Node dependency checks.
- Pros: easy dependency hygiene.
- Cons: no `web/package.json`; low value.
- Decision: reject.

### D) fd
- Link: https://github.com/sharkdp/fd
- License: Apache-2.0
- Activity (last commit / releases): pushed 2026-02-03; latest release `v10.3.0` (2025-08-26).
- Bundle size / deps: ~2.2 MB.
- Integration plan (exact files / APIs): fast file discovery in maintenance scripts.
- Pros: very fast and ergonomic.
- Cons: extra binary dependency; not needed because `rg --files` already used.
- Decision: reject.

## Final pick
- Chosen: manual reachability cleanup using repository-native analysis.
- Why: no dependency additions, highest confidence for mixed Qt/C++/web/doc repo.
- What code to copy / what API to call:
  - Use `rg` to find stale references.
  - Unify to `scripts/verify_repo.*` and remove placeholder verify entrypoints.
  - Remove non-runtime AI recipe/apply chains not referenced by runtime.

## Evidence
- GitHub REST API `repos/<owner>/<repo>` and `releases/latest` fetched on 2026-02-18.
