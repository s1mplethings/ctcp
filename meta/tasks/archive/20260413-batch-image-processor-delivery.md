# Task - s16-fixer-loop-pass

## Queue Binding

- Queue Item: `ADHOC-20260413-s16-fixer-loop-pass`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: repo-level canonical verify is still blocked by the single SimLab lite failure `S16_lite_fixer_loop_pass`, while the project-level delivery/replay chain already works.
- Dependency check: `ADHOC-20260413-csv-cleaner-full-review-bundle = doing`
- Scope boundary: only repair the concrete S16 fixer-loop failure path; do not broaden into unrelated delivery, replay, or project-generation changes.

## Task Truth Source (single source for current task)

- task_purpose:
  - identify the real first failing command inside `S16_lite_fixer_loop_pass`
  - apply the smallest code fix that makes the scenario pass again
  - prove the fix does not break virtual delivery, cold replay, or canonical verify
- allowed_behavior_change:
  - `simlab/generate_s16_fix_patch.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - do not weaken replay or completion-gate checks
  - do not hide repo-level failures behind project-level success
  - do not expand into large orchestrator or support refactors
  - do not change the scenario expectation unless the contract change is first proved
- in_scope_modules:
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `simlab/generate_s16_fix_patch.py`
  - focused SimLab logs and fixer-loop path
- out_of_scope_modules:
  - unrelated support delivery logic
  - CSV project content and review-bundle structure
  - broad workflow or docs cleanup
- completion_evidence:
  - `S16_lite_fixer_loop_pass` passes
  - `python simlab/run.py --suite lite` passes
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json` still passes
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` passes

## Analysis / Find (before plan)

- Entrypoint analysis: `S16_lite_fixer_loop_pass` fails before the second fixer-loop `advance`; the direct failing entrypoint is `python simlab/generate_s16_fix_patch.py --run-dir-file artifacts/_s16_run_dir.txt`.
- Downstream consumer analysis: the generated patch is consumed by the existing orchestrator fixer loop in the same run; if patch generation fails, the scenario cannot reach `VERIFY_PASSED`.
- Source of truth:
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260413-121602\summary.json`
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260413-121602\S16_lite_fixer_loop_pass\TRACE.md`
  - `simlab/generate_s16_fix_patch.py`
- Current break point / missing wiring: the S16 patch generator still assumes `meta/reports/LAST.md` contains the exact anchor `### Changes\n\n`, but the current report format no longer matches that hard-coded text, so patch generation exits before the fixer loop resumes.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream:
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml` step 5
- current_module:
  - `simlab/generate_s16_fix_patch.py`
- downstream:
  - `artifacts/diff.patch` inside the live S16 run
  - second `python scripts/ctcp_orchestrate.py advance --max-steps 16`
- source_of_truth:
  - S16 trace/logs and the generated patch file
- fallback:
  - if the generator still cannot build a patch, fail explicitly at the generator step with the first missing anchor or diff error
- acceptance_test:
  - `python simlab/generate_s16_fix_patch.py --run-dir-file artifacts/_s16_run_dir.txt`
  - `python simlab/run.py --suite lite`
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not remove the fixer-loop stage from S16
  - do not skip verify failure -> bundle -> fix -> pass sequencing
  - do not lower replay, package, or delivery requirements
- user_visible_effect:
  - repo-level verification returns to green without regressing the already-working delivery/replay chain

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: The real root cause of S16_lite_fixer_loop_pass is identified from the scenario definition, logs, and first failing command instead of guesswork
- [ ] DoD-2: A minimal repo change makes S16_lite_fixer_loop_pass pass again without lowering replay, completion-gate, or delivery standards
- [ ] DoD-3: After the fix, simlab lite, virtual delivery E2E, and canonical verify pass so the repo-level closure matches the already-working project-level delivery chain

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Confirm the first failing S16 command from the scenario, summary, TRACE, and stderr.
2) Patch only `simlab/generate_s16_fix_patch.py` so it can touch `LAST.md` against the current report structure.
3) Immediately rerun the patch generator against the existing failing S16 run.
4) Immediately rerun the smallest S16-related path.
5) Run `python simlab/run.py --suite lite`.
6) Run `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`.
7) Run `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`.
8) Record the first failure point and minimal fix strategy if any command still fails.
9) Completion criteria: prove `connected + accumulated + consumed` for the repaired fixer-loop path and the preserved delivery chain.

## Notes / Decisions

- Default choices made: prefer repairing the S16 patch generator's stale anchor assumption instead of touching scenario expectations or the delivery/replay code path.
- Alternatives considered: editing the S16 scenario to tolerate the failure; rejected because the first failing command is a real helper regression, not a valid contract change.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: treat this as a concrete SimLab helper regression if confirmed by the rerun; keep the fix scoped to the generator.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-workflow plus ctcp-gate-precheck for bind -> analyze -> minimal fix -> verify reporting.`

## Check / Contrast / Fix Loop Evidence

- check-1: the failing summary and TRACE both show the scenario stops at step 5, not in the second fixer-loop `advance`.
- contrast-1: the generator currently hard-codes `### Changes\n\n` as the only valid anchor in `meta/reports/LAST.md`, but the live report format no longer guarantees that exact text shape.
- fix-1: make the generator anchor against the current report structure in a format-tolerant way instead of assuming one exact `LAST.md` marker.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `simlab/generate_s16_fix_patch.py` can generate the replacement patch that S16 consumes
  - accumulated: the same S16 run proceeds through `VERIFY_FAILED`, `BUNDLE_CREATED`, and then `VERIFY_PASSED`
  - consumed: repo-level `simlab lite`, virtual delivery E2E, and canonical verify all use the repaired path without delivery/replay regressions

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary: root cause confirmed; code fix pending
- Queue status update suggestion (`todo/doing/done/blocked`): `doing`
