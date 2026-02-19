# Task — external-runs-root-and-teamnet

## Context
- Move default run artifacts for Team Mode / ADLC / SimLab to an external runs root.
- Keep repo-internal artifacts lightweight: pointers and path-logic metadata only.
- Add a clear multi-agent team network document with ADLC as the main execution spine.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [ ] Research logged (if needed): meta/externals/YYYYMMDD-external-runs-root-and-teamnet.md
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Spec-first (docs/spec/meta): path policy + teamnet docs
2) Implement (code if allowed): unified run-path resolver + callers
3) Verify (verify_repo + ctcp_team smoke)
4) Record (report + pointers + diff artifact)

## Notes / Decisions
- Default external runs root: `~/.ctcp/runs` (overridable by `CTCP_RUNS_ROOT`).
- Keep `verify_repo` replay behavior unchanged.

## Results
- Path policy switched to external runs root (`CTCP_RUNS_ROOT`, fallback `~/.ctcp/runs`).
- Team Mode / ADLC / SimLab defaults moved to external run directories.
- Repo-internal outputs restricted to lightweight pointers and path metadata.
- Added `docs/21_paths_and_locations.md` and `docs/22_agent_teamnet.md`.
- `scripts/verify_repo.ps1` passed; Team Mode smoke passed with external run pointer.
