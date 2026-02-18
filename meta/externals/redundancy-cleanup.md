# Externals Review — redundancy-cleanup

## Goal
- Find practical, low-risk ways to detect and prevent redundant files (temporary debug files, backups, duplicate payloads) from being committed.

## Constraints
- Offline only?: No (research online), but final checks must run locally.
- License constraints?: Prefer permissive licenses (MIT/Apache/BSD-like) for optional tooling.
- Must support Windows?: Yes.
- Must be vendorable?: Prefer "no" (tooling via CLI, avoid adding heavy vendored code).

## Candidates
### A) pre-commit
- Link: https://github.com/pre-commit/pre-commit
- License: MIT
- Activity (last commit / releases): pushed 2025-12-22; latest release `v4.5.1` at 2025-12-16.
- Bundle size / deps: repo size about 4.6 MB.
- Integration plan (exact files / APIs): add `.pre-commit-config.yaml`, run `pre-commit run --all-files` in CI/local.
- Pros: mature ecosystem, many existing hooks, good for "prevent commit" workflow.
- Cons: adds setup/runtime dependency and hook management overhead.
- Decision: reject for now. Good long-term, but overkill for current minimal cleanup patch.

### B) repolinter
- Link: https://github.com/todogroup/repolinter
- License: Apache-2.0
- Activity (last commit / releases): pushed 2026-02-06; latest release `v0.12.0` at 2025-05-09.
- Bundle size / deps: repo size about 4.1 MB.
- Integration plan (exact files / APIs): add `repolinter.json` rules and run in CI.
- Pros: policy-centric checks for repository hygiene.
- Cons: oriented to governance/docs conventions more than file-level temp artifact detection.
- Decision: reject for this task. Scope does not match the immediate redundant-file cleanup need.

### C) fclones
- Link: https://github.com/pkolaczk/fclones
- License: MIT
- Activity (last commit / releases): pushed 2025-03-03; latest release `v0.35.0` at 2025-03-03.
- Bundle size / deps: repo size about 0.9 MB.
- Integration plan (exact files / APIs): optional one-shot command `fclones group .` for duplicate content scan.
- Pros: strong duplicate-content detection, fast and focused.
- Cons: adds external binary dependency; does not enforce naming/policy by itself.
- Decision: partial use. Keep as optional manual scan tool, not a hard dependency.

### D) super-linter
- Link: https://github.com/super-linter/super-linter
- License: MIT
- Activity (last commit / releases): pushed 2026-02-17; latest release `v8.5.0` at 2026-02-07.
- Bundle size / deps: repo size about 43 MB.
- Integration plan (exact files / APIs): GitHub Action integration, containerized linter stack.
- Pros: comprehensive multi-language linting.
- Cons: too heavy for a local lightweight redundancy gate; CI-centric.
- Decision: reject. Tool weight is disproportionate to current requirement.

### E) fdupes
- Link: https://github.com/adrianlopezroche/fdupes
- License: `NOASSERTION` on GitHub API; upstream ships a custom permissive-style license file.
- Activity (last commit / releases): pushed 2025-12-15; latest release `v2.4.0` at 2025-03-30.
- Bundle size / deps: repo size about 0.3 MB.
- Integration plan (exact files / APIs): optional local dedupe scan command.
- Pros: classic duplicate-file scanner, small footprint.
- Cons: license metadata is ambiguous in GitHub API; weaker policy integration.
- Decision: reject for automated gate due license metadata ambiguity.

## Final pick
- Chosen: repository-local lightweight guard script + `.gitignore` hardening.
- Why: no new dependency, deterministic, fast, and directly enforceable from `scripts/verify_repo.*`.
- What code to copy / what API to call:
  - Add `tools/checks/redundancy_guard.py` and call it in verify scripts.
  - Block known temporary file names and tracked `*.bak` files.
  - Keep optional external tooling (`fclones`) as a manual aid, not mandatory.

## Evidence
- Source: GitHub REST API `repos/<owner>/<repo>` and `repos/<owner>/<repo>/releases/latest` on 2026-02-17.
