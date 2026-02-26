# Task - cos-user-v2p-dialogue-runner

## Queue Binding
- Queue Item: `N/A (user-requested feature implementation)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- User requested a deterministic/replayable CTCP workflow:
  - `python scripts/ctcp_orchestrate.py cos-user-v2p --repo ... --project ... --testkit-zip ...`
- Scope:
  - add CLI subcommand + doc-first evidence + dialogue recording
  - run external testkit outside CTCP repo and copy selected outputs to destination
  - run pre/post verify in target repo (unless explicit `--skip-verify`)
  - emit machine-readable `v2p_report.json`
  - add SimLab scenario, fixtures, behavior docs, and unit tests

## DoD Mapping (from request)
- [x] DoD-1: `cos-user-v2p` command available with required args and optional controls.
- [x] DoD-2: doc-first + dialogue artifacts + report generated in run_dir.
- [x] DoD-3: testkit runs outside CTCP repo and copies only requested outputs.
- [x] DoD-4: behavior registration + scenario + fixtures + unit test added.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: update task/report, behavior docs, and scenario contract.
2) Implement `cmd_cos_user_v2p` CLI wiring and dialogue-script compatibility fix.
3) Implement/finish `tools/testkit_runner.py` execution + copy + metrics helpers.
4) Add fixtures + unit test (`tests/test_cos_user_v2p_runner.py`).
5) Run targeted tests and then full gate `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
6) Record final verify evidence in `meta/reports/LAST.md`.

## Notes / Decisions
- Testkit execution is isolated to run_dir sandbox (`run_dir/sandbox/testkit`) to avoid repo pollution.
- Default destination is `D:/v2p_tests`; CI-safe fallback applies only when user does not explicitly pass `--out-root`.
- `--dialogue-script` accepts taskpack format (`ask/answer` with `ref`) and direct `qid->answer` format.
- Unit test uses temporary target repo with lightweight verify scripts for deterministic pre/post verify pass.
