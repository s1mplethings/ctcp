# Task - annotation-review-workbench-delivery

## Queue Binding

- Queue Item: `ADHOC-20260414-annotation-review-workbench-delivery`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: the user asked for a harder, more realistic CTCP project that behaves like real software rather than a lightweight utility page.
- Dependency check: `ADHOC-20260413-batch-image-processor-d-drive-bundle = done`
- Scope boundary: generate one external-run interactive annotation workbench with package, screenshot, delivery manifest, and cold replay evidence without broad repo refactors.

## Task Truth Source (single source for current task)

- task_purpose:
  - produce a locally runnable interactive annotation review workbench for image-folder loading, bounding-box editing, review status, notes, save/restore, and export
  - generate a real project package plus support_public_delivery.json with sent photo/document and completion_gate pass
  - prove the final package can cold replay and report the concrete artifact paths or the first real failure point
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - external run artifacts outside the repo
- forbidden_goal_shift:
  - do not ship a static mockup or fake interaction page
  - do not skip save/restore or export
  - do not skip package, delivery, or cold replay
  - do not broaden into unrelated repo repairs
- in_scope_modules:
  - external run_dir project for `Annotation Review Workbench`
  - project-local smoke/demo flow
  - package + public delivery closure
  - cold replay validation
- out_of_scope_modules:
  - unrelated support/orchestrate/replay refactors
  - unrelated benchmark or scenario work
  - repo contract redesign
- completion_evidence:
  - runnable project exists with README and clear entrypoint
  - project can load at least three images, create/edit/delete boxes, save/restore state, and export YOLO or COCO plus a stats report
  - screenshot, package, support_public_delivery.json, replay_report.json, and replayed_screenshot.png exist
  - final answer reports concrete artifact paths and real pass/fail status

## Analysis / Find (before plan)

- Entrypoint analysis: the easiest replay-compatible shape is still a dependency-light Python web app with `app.py`, local templates/static assets, and backend routes for project state plus export, while the browser layer provides the real annotation interactions.
- Downstream consumer analysis: the delivery closure consumes the finished screenshot and packaged zip; cold replay only needs the final package and a detectable `app.py` startup path.
- Source of truth:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `PATCH_README.md`
  - `TREE.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `tests/support_virtual_delivery_e2e_runner.py`
  - `scripts/support_public_delivery.py`
  - `scripts/delivery_replay_validator.py`
  - user-provided Annotation Review Workbench brief
- Current break point / missing wiring: no run-specific project exists yet; this task must create the external run_dir project, implement the interactive labeling workflow, and wire it into the already-working delivery and replay helpers.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream:
  - user brief for `Annotation Review Workbench`
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
  - actual project files, smoke/demo output, export files, manifest json, replay report, and screenshot files
- fallback:
  - if any stage fails, capture the first concrete failure point and return its real path instead of masking it
- acceptance_test:
  - project-local smoke for load/annotate/save/restore/export path
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not fake box editing without real persisted annotation data
  - do not skip export or restore
  - do not return only source code paths without the project package and evidence files
- user_visible_effect:
  - one real project run can be launched locally, used like an annotation tool, packaged, delivered, and replayed from the final zip

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: A runnable local interactive tool exists that loads an image set, supports bounding-box create/select/move/resize/delete with class labels, image navigation, per-image status and notes, undo/redo, auto-save, and project restore
- [ ] DoD-2: The project can save state and export at least one standard annotation format plus a simple statistics report, and it ships with README, package, and a high-value screenshot
- [ ] DoD-3: The support delivery closure emits support_public_delivery.json with sent photo/document and completion_gate.passed true, and cold replay writes replay_report.json plus replayed_screenshot.png with final answer reporting the concrete artifact paths or the first real failure point

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Create one D-drive external run root for the Annotation Review Workbench project and seed CTCP-shaped support/bound run folders.
2) Implement a dependency-light local web app with a real annotation canvas, project persistence, status/notes, and export routes.
3) Generate at least three local test images and run project-local smoke for load/annotate/save/restore/export.
4) Capture a high-value finished screenshot after a real interaction flow.
5) Build the final project zip and required metadata files.
6) Drive support public delivery in virtual mode so the run emits `support_public_delivery.json` with sent photo/document.
7) Run cold replay from the final package and collect `replay_report.json` plus `replayed_screenshot.png`.
8) Run repo-level regression commands and record the first failure point if any command fails.
9) Completion criteria: interactive runnable project + save/restore + export + package + delivery closure + cold replay + final artifact paths.

## Notes / Decisions

- Default choices made: prefer a simple Python + Flask + Pillow stack plus plain JavaScript interaction because it stays easy to rerun locally and easy for replay validation through `app.py`.
- Alternatives considered: a desktop GUI toolkit; rejected because it would add packaging and replay friction without improving the core CTCP delivery proof chain enough for this task.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: treat any failure as a run-specific project or packaging blocker first; only pivot to repo repair if the shared delivery/replay helpers themselves fail.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-workflow discipline for bind -> build -> show -> verify, while reusing the repo's delivery and replay helpers.`

## Check / Contrast / Fix Loop Evidence

- check-1: the annotation workbench must create and persist real box coordinates and labels, not just draw temporary front-end shapes.
- contrast-1: a visual-only canvas demo would satisfy screenshots but fail save/restore/export credibility.
- fix-1: keep project state authoritative on the backend and write/export concrete annotation files before packaging.
- check-2: the final package must still cold replay from its own entrypoint.
- contrast-2: a source tree that only works from the original workspace is not enough for CTCP delivery proof.
- fix-2: keep the project self-contained with `app.py`, `requirements.txt`, README, and in-package startup instructions.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: the generated project can launch locally, load images, persist annotation state, and export outputs through real files
  - accumulated: the run collects smoke/demo output, screenshot, package, support_public_delivery.json, and replay evidence
  - consumed: the final answer points to the exact artifacts the user needs to inspect and reuse

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary: pending implementation
- Queue status update suggestion (`todo/doing/done/blocked`): `doing`
