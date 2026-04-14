# Task - batch-image-processor-delivery

## Queue Binding

- Queue Item: `ADHOC-20260413-batch-image-processor-delivery`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: the user asked for one real Batch Image Processor project to exercise CTCP project generation, package delivery, and cold replay as an end-to-end proof chain.
- Dependency check: `ADHOC-20260413-s16-fixer-loop-pass = doing`
- Scope boundary: build one external-run local web project plus its smoke, screenshot, package, delivery manifest, and replay evidence without broad repo refactors.

## Task Truth Source (single source for current task)

- task_purpose:
  - produce a runnable local web tool for batch image upload, processing, preview, single download, and zip download
  - generate a real project package plus support_public_delivery.json with sent photo/document and completion_gate pass
  - prove the final package can cold replay and report final artifact paths or the first concrete failure point
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - external run artifacts outside the repo
- forbidden_goal_shift:
  - do not ship a static or fake-processing demo
  - do not skip package, delivery, or cold replay
  - do not broaden into unrelated repo repairs
  - do not claim success without real screenshot, zip, and manifest artifacts
- in_scope_modules:
  - external run_dir project for `Batch Image Processor`
  - package + public delivery closure
  - cold replay validation
- out_of_scope_modules:
  - unrelated support/orchestrate refactors
  - benchmark/report bundle work unrelated to this project
  - scenario expectation edits
- completion_evidence:
  - runnable project exists with README and clear entrypoint
  - screenshot, package, support_public_delivery.json, replay_report.json, and replayed_screenshot.png exist
  - final answer reports concrete paths and real pass/fail status

## Analysis / Find (before plan)

- Entrypoint analysis: the simplest replay-compatible delivery shape is a dependency-light Python web app with `app.py`, local `templates/` and `static/`, plus a generated zip package consumed by `scripts/delivery_replay_validator.py`.
- Downstream consumer analysis: the delivery closure consumes project screenshots and the packaged zip; cold replay only needs the final package and a detectable `app.py`.
- Source of truth:
  - `AGENTS.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `scripts/support_public_delivery.py`
  - `scripts/delivery_replay_validator.py`
  - `tests/support_virtual_delivery_e2e_runner.py`
  - user-provided Batch Image Processor brief
- Current break point / missing wiring: no run-specific project exists yet; this task must create the external run_dir project and wire it into the already-working virtual delivery + replay helpers.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream:
  - user brief for `Batch Image Processor`
  - repo delivery helpers in `scripts/support_public_delivery.py`
- current_module:
  - external run_dir project output
  - support-session delivery closure
  - replay validation output
- downstream:
  - final project zip
  - `support_public_delivery.json`
  - `replay_report.json`
  - `replayed_screenshot.png`
- source_of_truth:
  - actual project files, smoke output, manifest json, replay report, and screenshot files
- fallback:
  - if any stage fails, capture the first concrete failure point and return its real path instead of masking it
- acceptance_test:
  - project-local smoke for upload/process/download path
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not simulate image processing in the UI without generating real output files
  - do not skip support delivery or cold replay
  - do not return only source code paths without the project package and evidence files
- user_visible_effect:
  - one real project run can be launched locally, packaged, delivered, and replayed from the final zip

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: A runnable local web project exists that supports batch image upload, real processing, preview, single download, and zip download with README and clear entrypoint
- [ ] DoD-2: The project emits a real high-value screenshot, a final project package, support_public_delivery.json with sent photo and document, empty errors, and completion_gate.passed true
- [ ] DoD-3: Cold replay succeeds from the final package and writes replay_report.json plus replayed_screenshot.png, with final answer reporting concrete artifact paths or the first real failure point

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Create one external run root for the Batch Image Processor project and seed CTCP-shaped support/bound run folders.
2) Implement a dependency-light local web app with real batch image processing and downloadable outputs.
3) Run project-local smoke against at least three images and collect real processed outputs.
4) Capture a high-value finished screenshot for the project.
5) Build the final project zip and required metadata files.
6) Drive support public delivery in virtual mode so the run emits `support_public_delivery.json` with sent photo/document.
7) Run cold replay from the final package and collect `replay_report.json` plus `replayed_screenshot.png`.
8) Run repo-level regression commands and record the first failure point if any command fails.
9) Completion criteria: runnable project + package + delivery closure + cold replay + final artifact paths.

## Notes / Decisions

- Default choices made: prefer a simple Python + Flask + Pillow stack because it is easy to rerun locally and easy for replay validation through `app.py`.
- Alternatives considered: a heavier JS build pipeline; rejected because it adds replay friction without helping the core image-processing proof chain.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: treat any failure as a run-specific project or packaging blocker first; only pivot to repo repair if the shared delivery/replay helpers themselves fail.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-workflow discipline for bind -> build -> show -> verify, while reusing the repo's delivery and replay helpers.`

## Check / Contrast / Fix Loop Evidence

- check-1: the project must process real image files and emit real outputs, not only front-end placeholders.
- contrast-1: a static HTML page or fake preview would satisfy screenshots but fail package, delivery, and replay credibility.
- fix-1: keep processing on the backend with actual output files under a generated output directory before packaging.
- check-2: the final package must still cold replay from its own entrypoint.
- contrast-2: a source tree that only works from the original workspace is not enough for CTCP delivery proof.
- fix-2: keep the project self-contained with `app.py`, `requirements.txt`, README, and in-package startup instructions.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: the generated project can launch locally and process uploaded images into real output files
  - accumulated: the run collects smoke output, screenshot, package, support_public_delivery.json, and replay evidence
  - consumed: the final answer points to the exact artifacts the user needs to inspect and reuse

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary: pending implementation
- Queue status update suggestion (`todo/doing/done/blocked`): `doing`
