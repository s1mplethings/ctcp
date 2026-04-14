# Task - csv-cleaner-full-review-bundle

## Queue Binding

- Queue Item: `ADHOC-20260413-csv-cleaner-full-review-bundle`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: the user asked for one serious CTCP rehearsal that yields a real small project plus a full evidence bundle for external review.
- Dependency check: `ADHOC-20260413-cold-delivery-replay-gate = doing`
- Scope boundary: create one real CSV cleaner web-tool run and package its evidence without mixing in unrelated repo repairs.

## Task Truth Source (single source for current task)

- task_purpose:
  - execute a genuine CTCP project-delivery rehearsal using the fixed CSV cleaner web-tool brief
  - produce a runnable project with smoke proof, finished screenshot, project package, support delivery manifest, and cold replay evidence
  - assemble a human-reviewable bundle that includes task records, process notes, environment manifest, command outputs, and final artifacts
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `artifacts/**`
- forbidden_goal_shift:
  - do not replace the real project with a toy placeholder or only a benchmark report
  - do not omit failed checks from the final bundle
  - do not package only code without delivery/replay/environment evidence
  - do not broaden into unrelated repo refactors
- in_scope_modules:
  - external run_dir project output for the CSV cleaner tool
  - support delivery and cold replay evidence generation
  - reviewer-facing bundle assembly under `artifacts/`
- out_of_scope_modules:
  - unrelated repo behavior repairs
  - prompt/style contract rework
  - architectural cleanup outside this run
- completion_evidence:
  - runnable CSV cleaner project exists with README and entrypoint
  - final screenshot, project zip, support delivery manifest, and replay artifacts exist
  - reviewer bundle zip exists with INDEX and command/result evidence

## Analysis / Find (before plan)

- Entrypoint analysis: the narrowest end-to-end path is to materialize a CTCP-shaped project under one external run, then let `scripts/support_public_delivery.py` package it and `scripts/delivery_replay_validator.py` prove cold restart from the final zip.
- Downstream consumer analysis: the reviewable sink is the bundle zip in `artifacts/`, while delivery truth still flows through `support_public_delivery.json` and `frontend.delivery_reply_actions.evaluate_delivery_completion`.
- Source of truth:
  - `AGENTS.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `scripts/support_public_delivery.py`
  - `scripts/delivery_replay_validator.py`
  - user-provided task brief in chat
- Current break point / missing wiring: CTCP already has delivery/replay helpers, but this repo still lacks one packaged real-project rehearsal bundle that external reviewers can inspect end-to-end.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream:
  - user task brief
  - repo delivery helpers under `scripts/support_public_delivery.py`
- current_module:
  - external run_dir project output
  - `artifacts/csv_cleaner_full_review_bundle/**`
- downstream:
  - `support_public_delivery.json`
  - `replay_report.json`
  - `artifacts/csv_cleaner_full_review_bundle.zip`
- source_of_truth:
  - final run artifacts copied into the review bundle
- fallback:
  - if any command fails, capture its exact command, exit code, and first failure point in the report bundle instead of hiding it
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - project-local smoke and replay commands recorded in the bundle
- forbidden_bypass:
  - do not claim completion from screenshots alone
  - do not claim delivery closure without manifest plus replay evidence
  - do not hide repo-level gate failures if they occur
- user_visible_effect:
  - an external reviewer can unzip one bundle and inspect the task, project, screenshots, environment, verify outputs, delivery manifest, and replay evidence in one place

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: A real runnable CSV upload/clean/export web tool is produced with README, smoke evidence, packaged project artifact, and a high-value finished screenshot
- [ ] DoD-2: The support delivery closure emits support_public_delivery.json with sent photo/document, completion_gate.passed true, and cold replay evidence including replay_report.json plus replayed_screenshot.png
- [ ] DoD-3: A reviewer-facing bundle under artifacts contains task record, process log, environment manifest, delivery evidence, verify/simlab/workflow outputs, and an INDEX that explains how to re-check the run

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed (explicitly `Docs/meta/artifacts only; no repo code dirs touched`)
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Rebind the task and record the fixed brief for the real CSV cleaner project.
2) Materialize one external run_dir with a real CTCP-shaped web project and seed task/process evidence.
3) Run project-local smoke, collect actual UI screenshot(s), and package the project.
4) Drive support delivery closure and cold replay over the packaged project.
5) Run the repo-level checks requested by the user and capture pass/fail outputs verbatim.
6) Assemble `00_task`..`05_reports` plus `INDEX.md`, then zip the final review bundle.
7) Record the first failure point for every failed command and keep the bundle auditable.
8) Canonical verify gate: `scripts/verify_repo.*`
9) Completion criteria: prove runnable project + delivery closure + cold replay + reviewer bundle.

## Notes / Decisions

- Default choices made: build the CSV cleaner as a dependency-light Python web app so the package can be cold-replayed without extra services.
- Alternatives considered: using the generic built-in web-service archetype; rejected because it would not satisfy the user's concrete CSV upload/clean/export tool brief.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: no new repo runtime defect is assumed upfront; if repo-level gates fail, record them as observed failures in the review bundle rather than turning this run into a broad repair task.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-workflow plus ctcp-gate-precheck for task binding, gate execution, and auditable reporting.`

## Check / Contrast / Fix Loop Evidence

- check-1: `python scripts/workflow_checks.py` must pass before any artifact-heavy execution is credible.
- contrast-1: the first precheck failure showed missing workflow-evidence sections in `CURRENT.md`, which would make all later results non-compliant even if the project run itself succeeded.
- fix-1: add explicit `Check / Contrast / Fix Loop Evidence` and `Completion Criteria Evidence` sections before starting the real project run.
- check-2: the review bundle must prove delivery from the final packaged project, not just from a working source tree.
- contrast-2: screenshots or a standalone project folder are insufficient because external review also needs manifest, replay, environment, and command evidence.
- fix-2: run support delivery and cold replay against the packaged zip, then copy the resulting artifacts into the final review bundle.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: the real CSV cleaner project is runnable from its packaged entrypoint and has smoke plus screenshot evidence
  - accumulated: the run captures task record, process log, environment manifest, delivery manifest, replay report, and requested repo-level command outputs
  - consumed: the final reviewer bundle organizes those artifacts under `00_task`..`05_reports` with `INDEX.md` so an external reviewer can inspect and reuse them without repo-local context
- 完成标准:
  - runnable project, support delivery, and cold replay all leave concrete artifacts
  - the final bundle zip exists and points reviewers to the right files first
  - failed checks, if any, are reported with exact command and first failure point

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary: real CSV cleaner project, support delivery, and cold replay passed; repo-level `workflow_checks` and virtual delivery E2E passed; repo-level `simlab lite` and `verify_repo` failed on existing `S16_lite_fixer_loop_pass`.
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
