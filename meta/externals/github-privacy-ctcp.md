# Externals Review — github-privacy-ctcp

## Goal
- Prevent private/local files from being uploaded to GitHub and align public project naming to `ctcp`.

## Constraints
- Offline only?: No, but implementation must be repo-local and deterministic.
- License constraints?: Prefer permissive/open tooling only.
- Must support Windows?: Yes.
- Must be vendorable?: Yes; no required new runtime dependency.

## Candidates
### A) github/gitignore
- Link: https://github.com/github/gitignore
- License: CC0-1.0
- Activity (last commit / releases): 4,082 commits; last commit date 2026-02-17.
- Bundle size / deps: Template-only repository; zero runtime deps.
- Integration plan (exact files / APIs): Reuse patterns in root `.gitignore`.
- Pros: Official template source; low risk.
- Cons: Generic templates still need project-specific tuning.
- Decision: use as baseline.

### B) gitleaks/gitleaks
- Link: https://github.com/gitleaks/gitleaks
- License: MIT
- Activity (last commit / releases): repo listing shows updated 2026-01-08.
- Bundle size / deps: Extra binary/tooling required.
- Integration plan (exact files / APIs): Optional future CI secret scan stage.
- Pros: Strong secret scanning coverage.
- Cons: Additional tooling cost; not required for this minimal patch.
- Decision: reject for now (keep as optional follow-up).

### C) Yelp/detect-secrets
- Link: https://github.com/Yelp/detect-secrets
- License: Apache-2.0
- Activity (last commit / releases): latest release v1.5.0 on 2025-06-16.
- Bundle size / deps: Python package dependency.
- Integration plan (exact files / APIs): Optional pre-commit hook.
- Pros: Mature policy-based secret scanning.
- Cons: Adds setup/maintenance overhead.
- Decision: reject for now.

### D) awslabs/git-secrets
- Link: https://github.com/awslabs/git-secrets
- License: Apache-2.0
- Activity (last commit / releases): latest release v1.3.0 on 2020-08-13.
- Bundle size / deps: Shell tooling, lightweight.
- Integration plan (exact files / APIs): Optional local git hooks.
- Pros: Simple hook-based prevention.
- Cons: Older release cadence; lower flexibility than policy scanners.
- Decision: reject for now.

## Final pick
- Chosen: `.gitignore` hardening with project-specific privacy patterns + CMake/project naming alignment.
- Why: No new dependencies, lowest risk, immediate effect for GitHub uploads.
- What code to copy / what API to call:
  - Apply curated ignore rules in `.gitignore`.
  - Rename CMake project target to `ctcp` for build artifact name consistency.

## Evidence
- GitHub repository and release pages accessed on 2026-02-18.
