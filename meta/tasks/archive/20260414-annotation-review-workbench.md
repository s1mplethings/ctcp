# Task - batch-image-processor-d-drive-bundle

## Queue Binding

- Queue Item: `ADHOC-20260413-batch-image-processor-d-drive-bundle`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: the user asked to place the completed Batch Image Processor outputs on `D:` and hand over one complete package instead of scattered runtime paths on `C:`.
- Dependency check: `ADHOC-20260413-batch-image-processor-delivery = done`
- Scope boundary: reorganize the existing external-run artifacts into one reviewer-facing D-drive bundle without regenerating or redesigning the project.

## Task Truth Source (single source for current task)

- task_purpose:
  - preserve the already-completed Batch Image Processor project package and evidence files
  - copy the reviewer-relevant outputs into a D-drive bundle directory with clear structure and human-readable records
  - compress that review directory into one zip and report the retained key artifact paths
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - repo `artifacts/` bundle outputs
- forbidden_goal_shift:
  - do not rebuild the project or change its behavior
  - do not rerun unrelated repo repairs
  - do not omit delivery/replay evidence from the final bundle
  - do not claim the bundle is complete if a required artifact is missing; record the gap instead
- in_scope_modules:
  - the completed external run for `Batch Image Processor`
  - D-drive review-bundle directory and zip
  - task/environment/process manifest files for the bundle
- out_of_scope_modules:
  - project feature changes
  - support/orchestrate/replay code changes
  - unrelated benchmark or scenario work
- completion_evidence:
  - D-drive review directory exists with `00_task` through `05_reports` plus `INDEX.md`
  - project zip, screenshot, support_public_delivery.json, replay_report.json, and replayed_screenshot.png are present in the bundle
  - final answer reports the D-drive bundle zip path and the retained key artifact paths

## Analysis / Find (before plan)

- Entrypoint analysis: the active user need is a reviewer-facing D-drive package, so the main deliverable is a bundle directory and zip rather than a new generation run.
- Downstream consumer analysis: the bundle consumer is a human reviewer who needs the package, screenshot, delivery manifest, replay proof, and a clear index in one place.
- Source of truth:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/archive/20260413-batch-image-processor-delivery.md`
  - completed run artifacts under `C:\Users\sunom\.ctcp\runs\ctcp\20260413-batch-image-processor-delivery`
  - user instruction to place the outputs on `D:` and package everything together
- Current break point / missing wiring: the project succeeded, but the outputs still live as scattered C-drive runtime artifacts rather than one D-drive review bundle.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream:
  - completed Batch Image Processor external run on `C:`
- current_module:
  - D-drive review-bundle assembly
- downstream:
  - one reviewer-facing zip and directory under repo `artifacts/`
- source_of_truth:
  - real files copied from the completed run plus generated bundle records
- fallback:
  - if any source artifact is missing, keep building the bundle but record the concrete missing path in `INDEX.md`
- acceptance_test:
  - artifact existence checks against the completed run
  - bundle zip creation on D drive
- forbidden_bypass:
  - do not omit project or evidence files
  - do not substitute a docs-only zip for the real project package
  - do not hide missing artifacts
- user_visible_effect:
  - the user can inspect or forward one D-drive zip instead of chasing scattered C-drive runtime outputs

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: A D-drive review directory contains the final project package, unpacked project copy, screenshots, delivery manifest, replay evidence, and reviewer-facing task/process/environment records
- [ ] DoD-2: The review directory is compressed into one zip under repo artifacts and its INDEX clearly explains contents plus any missing or failed items
- [ ] DoD-3: The final answer reports the D-drive bundle path together with the retained project package, screenshot, support_public_delivery.json, and replay_report.json paths

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed (`Docs-only, no code dirs touched`)
- [x] Overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Verify the existing Batch Image Processor package/evidence files still exist.
2) Create a D-drive review directory with the required `00_task` through `05_reports` structure.
3) Copy the completed project package, unpacked project copy, screenshots, delivery manifest, and replay artifacts into the bundle.
4) Write reviewer-facing records: original task brief, task conversation record, environment manifest, command summary, and `INDEX.md`.
5) Compress the review directory into one zip under repo `artifacts/`.
6) Report the D-drive bundle path and retained key artifact paths.

## Notes / Decisions

- Default choices made: keep the already-completed C-drive run as the source of truth and produce a D-drive mirror bundle instead of moving or mutating the original run.
- Alternatives considered: physically move the original run root to D drive; rejected because it could break the already-generated manifest and replay references.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: treat any missing artifact as a bundle-assembly blocker and record it in the bundle index instead of silently substituting it.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-workflow discipline for bind -> bundle -> verify artifact presence -> close.`

## Check / Contrast / Fix Loop Evidence

- check-1: the D-drive bundle must contain the real project zip plus the real screenshot, delivery manifest, and replay artifacts rather than only pointers back to the C-drive run.
- contrast-1: a docs-only bundle or a bundle that only lists source paths would still force reviewers to hunt through runtime folders and would fail the user request.
- fix-1: copy the concrete project and evidence files into the bundle tree and keep the source C-drive paths as references inside the written manifests.
- check-2: the bundle must remain understandable if any artifact is missing.
- contrast-2: silently skipping a missing file would make the package look complete while weakening review trust.
- fix-2: have `INDEX.md` and the command summary call out any missing or failed item explicitly.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: the bundle links the original run, the copied project package, the copied evidence files, and the reviewer-facing manifests in one place
  - accumulated: the D-drive directory and zip preserve the project copy, images, delivery/replay artifacts, and environment/process records
  - consumed: the final answer reports the D-drive bundle paths so the user can directly review or forward them

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary: `workflow_checks`, project smoke, virtual delivery E2E, `simlab --suite lite`, and `verify_repo.ps1 -Profile code` all passed after bundle-task metadata fixes; D-drive review bundle directory and zip were created under repo `artifacts/`.
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
