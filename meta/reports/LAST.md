# Demo Report - LAST

## Goal
- Complete `L2-FAIL-001`: enforce hard fail evidence (`failure_bundle.zip`) and fixer loop convergence (`FAIL -> new patch -> PASS`) with lite regressions.
- Keep contracts unchanged: resolver-first, `find_result.json` as decision authority, external `CTCP_RUNS_ROOT` run dirs, no new dependencies, no real networking.

## Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/12_modules_index.md`
- `docs/30_artifact_contracts.md`
- `meta/tasks/TEMPLATE.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`

## Plan
1. Docs/spec first:
   - align artifact contract wording for `verify_report.json` and `failure_bundle.zip`.
2. Code:
   - harden `ctcp_orchestrate.py` fail path and fixer loop.
3. Regression:
   - strengthen S15 assertions (paths field + fixer outbox prompt).
4. Verify:
   - `sync_doc_links --check`
   - `simlab/run.py --suite lite`
   - `scripts/verify_repo.ps1`
   - clean-worktree `git apply --check`
5. Report:
   - record evidence paths and demo pointers.

## Timeline / Trace Pointer
- Lite suite run evidence:
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260219-200922`
- S15 external run demo (failure bundle + fixer outbox):
  - `C:\Users\sunom\AppData\Local\ctcp\runs\sandbox\20260219-201006-016278-orchestrate`
- S16 external run demo (loop to pass):
  - `C:\Users\sunom\AppData\Local\ctcp\runs\sandbox\20260219-201021-005256-orchestrate`

## Changes
- Unified diff patch:
  - `PATCHES/20260219-failure-closure-loop.patch`
- `meta/tasks/CURRENT.md`
  - switched active task binding to `L2-FAIL-001`, kept code-change gate enabled.
- `meta/backlog/execution_queue.json`
  - marked `L2-FAIL-001` as `done` with S15/S16 closure note.
- `scripts/ctcp_orchestrate.py`
  - added verify iteration control (`verify_iterations`, max read from `PLAN.md` or `guardrails.md`, default `3`).
  - added stop event/status on limit hit: `STOP_MAX_ITERATIONS`.
  - added tracked-dirty apply safety gate before `git apply` (`repo_dirty_before_apply`), while allowing managed fixer delta over prior applied patch.
  - added command trace blocks in `TRACE.md` for apply/verify/retry/revert with cmd, exit_code, stdout/stderr tail.
  - hardened verify report output with required fields:
    - `result`, `commands`, `failures`, `paths` (+compat mirror `artifacts`).
  - fail path now always:
    - writes `VERIFY_FAILED`
    - ensures/validates `failure_bundle.zip`
    - writes `BUNDLE_CREATED`
    - dispatches fixer outbox prompt immediately (`OUTBOX_PROMPT_CREATED`).
  - bundle validation now requires `reviews/*` and `outbox/*` entries when those files exist.
  - fail-state outbox dispatch no longer downgrades run status from `fail` to `blocked`.
  - adds optional backup of previously applied patch on fixer re-iteration (`artifacts/diff.patch.iter<N>.bak`).
- `simlab/scenarios/S15_lite_fail_produces_bundle.yaml`
  - added assertions for `verify_report.paths`.
  - added assertions for fixer outbox prompt content (`Role: fixer`, `failure_bundle.zip`, `write to: artifacts/diff.patch`).
- `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - locks same-run fail->fix->pass convergence and asserts `VERIFY_PASSED`.
- `tests/fixtures/patches/lite_fail_bad_readme_link.patch`
  - deterministic fail patch used by S15/S16.
- `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - deterministic fixer patch used by S16 pass loop.
- `docs/30_artifact_contracts.md`
  - expanded `verify_report.json` minimum fields (iteration fields + `paths`).
  - expanded failure bundle minimum list to include `reviews/*` and `outbox/*` when present.

## Verify
- `python scripts/sync_doc_links.py --check`
  - result: `[sync_doc_links] ok`
- `python simlab/run.py --suite lite`
  - result: `{"run_dir":".../simlab_runs/20260219-200922","passed":8,"failed":0}`
  - includes new hard regressions:
    - `S15_lite_fail_produces_bundle` pass
    - `S16_lite_fixer_loop_pass` pass
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - result: `[verify_repo] OK`
  - key lines:
    - ctest lite: `2/2` pass
    - workflow checks: ok
    - contract checks: ok
    - doc index check: ok
    - lite replay: `passed=8 failed=0`
- clean-worktree patch apply check:
  - command: `git -C <temp_worktree> apply --check PATCHES/20260219-failure-closure-loop.patch`
  - result: pass
- S15 evidence excerpt:
  - `_s15_events.jsonl` contains `VERIFY_STARTED`, `VERIFY_FAILED`, `BUNDLE_CREATED`, `OUTBOX_PROMPT_CREATED`.
  - `_s15_advance.out.txt` shows outbox creation and failure bundle path.
- S16 evidence excerpt:
  - `_s16_verify_report.json` result is `PASS` with `iteration: 2`.
  - `_s16_events.jsonl` contains `VERIFY_FAILED`, `BUNDLE_CREATED`, `VERIFY_PASSED`.

## Open Questions
- None.

## Next Steps
1. Add an explicit lite case for `STOP_MAX_ITERATIONS` to lock the new stop condition.
