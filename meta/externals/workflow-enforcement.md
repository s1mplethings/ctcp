# Externals Review — workflow-enforcement

## Goal
- Enforce repo workflow in code (not only docs): hard gate for code changes, unified verify entrypoint, and deterministic operator helper tooling.

## Constraints
- Offline only?: No (research online), but execution is local and deterministic.
- License constraints?: Prefer permissive licenses.
- Must support Windows?: Yes.
- Must be vendorable?: Yes; avoid mandatory new runtime dependencies.

## Candidates
### A) pre-commit
- Link: https://github.com/pre-commit/pre-commit
- License: MIT
- Activity (last release): `v4.5.1` on 2025-12-16.
- Bundle size / deps: Python package + hook setup.
- Integration plan: move policy checks into git hooks.
- Pros: mature ecosystem, hook chaining.
- Cons: requires per-clone hook install and local git integration; not a single verify gate by itself.
- Decision: reject for primary gate, keep optional.

### B) Lefthook
- Link: https://github.com/evilmartians/lefthook
- License: Apache-2.0
- Activity (repo active, 2.x line): project page and repo show active 2025 updates.
- Bundle size / deps: external binary/tooling.
- Integration plan: replace hook management and run checks before commit.
- Pros: fast, polyglot.
- Cons: adds external dependency and config migration.
- Decision: reject for this patch.

### C) just
- Link: https://github.com/casey/just
- License: CC0-1.0
- Activity (last release): `1.43.1` on 2025-11-12.
- Bundle size / deps: single binary, but extra install step.
- Integration plan: replace shell/ps1 verify scripts with just recipes.
- Pros: clean task UX.
- Cons: introduces mandatory extra tool for contributors and CI images.
- Decision: reject for this patch.

### D) nox
- Link: https://github.com/wntrblm/nox
- License: Apache-2.0
- Activity: active docs/releases in 2025-2026 line.
- Bundle size / deps: Python package + noxfile migration.
- Integration plan: encode checks as nox sessions.
- Pros: good Python automation model.
- Cons: repo is mixed C++/Qt + scripts; nox would not simplify CMake/web gates enough.
- Decision: reject for this patch.

## Final pick
- Chosen: native script enforcement in-repo (`scripts/workflow_checks.py` + `scripts/verify_repo.*` as full gate) + small helper tool (`tools/ctcp_assistant.py`).
- Why:
  - no new dependency
  - immediate enforcement in existing CI/local entrypoint
  - compatible with current cross-platform scripts
- What code to copy / what API to call:
  - add `scripts/workflow_checks.py` and call from `scripts/verify_repo.*`
  - make `scripts/verify.*` thin wrappers
  - add task/externals scaffolding generator in `tools/ctcp_assistant.py`

## Evidence
- pre-commit repo and releases: https://github.com/pre-commit/pre-commit , https://github.com/pre-commit/pre-commit/releases
- Lefthook repo: https://github.com/evilmartians/lefthook
- just repo and releases: https://github.com/casey/just , https://github.com/casey/just/releases
- nox repo/docs: https://github.com/wntrblm/nox , https://nox.thea.codes/en/stable/CHANGELOG.html
- Accessed on 2026-02-18.
