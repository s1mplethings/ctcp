# Externals Review — repo-rename-gate-convergence

## Goal
- Resolve post-rename drift (`ctcp`) and reduce operator/agent failure by converging build+verify entrypoints and removing broken instructions.

## Constraints
- Offline only?: No (research online), execution remains local.
- License constraints?: Prefer permissive licenses.
- Must support Windows?: Yes.
- Must be vendorable?: Yes, avoid adding mandatory dependencies.

## Candidates
### A) just
- Link: https://github.com/casey/just
- License: CC0-1.0
- Activity (last commit / releases): latest release `1.43.0` on 2025-09-01.
- Bundle size / deps: standalone binary.
- Integration plan (exact files / APIs): replace `scripts/verify*` with `just verify`.
- Pros: simple task runner, good DX.
- Cons: introduces new required tool for all contributors/CI.
- Decision: reject for this patch.

### B) go-task / Taskfile
- Link: https://github.com/go-task/task
- License: MIT
- Activity (last commit / releases): latest release `v3.45.5` on 2025-11-11.
- Bundle size / deps: standalone binary.
- Integration plan (exact files / APIs): add `Taskfile.yml`, migrate build/verify commands.
- Pros: strong cross-platform command orchestration.
- Cons: extra dependency and migration cost.
- Decision: reject for this patch.

### C) tox
- Link: https://github.com/tox-dev/tox
- License: MIT
- Activity (last commit / releases): latest release `4.32.0` on 2025-08-24.
- Bundle size / deps: Python package + config migration.
- Integration plan (exact files / APIs): tox env as canonical gate.
- Pros: mature matrix/gating for Python projects.
- Cons: repo is mixed C++/Qt + scripts; tox is not a great fit as global gate.
- Decision: reject.

### D) nox
- Link: https://github.com/wntrblm/nox
- License: Apache-2.0
- Activity (last commit / releases): changelog includes 2025.10.16 release line.
- Bundle size / deps: Python package + noxfile.
- Integration plan (exact files / APIs): model gates as nox sessions.
- Pros: flexible Python automation.
- Cons: still adds dependency and doesn't simplify CMake entrypoint by itself.
- Decision: reject.

## Final pick
- Chosen: keep native shell/PowerShell scripts, define one public gate entrypoint (`scripts/verify.*`) that delegates to `scripts/verify_repo.*` + contract checks.
- Why:
  - zero new dependencies
  - immediate compatibility with current docs/project scanner
  - preserves repository contract (`verify_repo`) while removing placeholder behavior.
- What code to copy / what API to call:
  - update `scripts/verify.ps1` and `scripts/verify.sh` to orchestrate existing scripts.
  - align naming (`ctcp`) across CMake/build/verify docs.
  - remove dead guidance in `PATCH_README.md` and fix missing bootstrap script with `build_v6.cmd`.

## Evidence
- GitHub repo rename behavior docs: https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository
- CMake `project()` reference: https://cmake.org/cmake/help/latest/command/project.html
