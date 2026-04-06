# Task - support-delivery-evidence-surface

## Queue Binding

- Queue Item: `ADHOC-20260406-support-delivery-evidence-surface`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: the repo can generate and package project outputs, but the frontend/support result path still collapses completion into generic text and raw paths instead of directly showing user-facing delivery evidence.
- Dependency check:
  - `ADHOC-20260406-vtuber-highlight-local-mvp` = `done`
  - `ADHOC-20260405-project-intent-mvp-mainline-shift` = `done`
- Scope boundary: make delivery evidence a first-class backend/frontend artifact so the support-facing completion path can directly present reports, screenshots, demo media, structured outputs, verification summary, limitations, and next actions.

## Task Truth Source

- task_purpose: add a stable delivery evidence manifest and wire it through the backend result object, bridge payloads, and frontend completion rendering so users can see delivery results directly in support/frontend replies.
- allowed_behavior_change:
  - `contracts/schemas/`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/project_delivery_evidence_bridge.py`
  - `apps/project_backend/`
  - `apps/cs_frontend/`
  - `tests/backend/test_backend_service.py`
  - `tests/frontend/test_frontend_handler.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260406-vtuber-highlight-local-mvp.md`
  - `meta/reports/archive/20260406-vtuber-highlight-local-mvp.md`
- forbidden_goal_shift:
  - do not focus this patch on producing more packaged project assets
  - do not leave frontend completion as generic free text with hidden evidence buried in raw artifacts
  - do not make the frontend scan directories ad hoc to guess which files are important
- in_scope_modules:
  - backend delivery result assembly
  - bridge result/evidence capabilities
  - frontend result object and completion rendering
  - focused tests for evidence propagation and user-facing rendering
- out_of_scope_modules:
  - generating new sample projects
  - broad support bot delivery packaging heuristics outside the active frontend/backend mainline
  - top-level north-star or README rewrites
- completion_evidence: backend emits a structured delivery evidence manifest, the frontend completion object explicitly carries it, customer-facing completion text shows evidence summary/user next steps, focused tests pass, and canonical verify closes.

## Analysis / Find

- Entrypoint analysis: the active mainline is `apps/cs_frontend/* -> apps/project_backend/* -> scripts/ctcp_front_bridge.py`, not the older free-form `frontend/response_composer.py` path.
- Downstream consumer analysis: the support/frontend lane needs a user-facing evidence block, not just `run_dir`, `repo_report_tail`, or raw `artifacts` dictionaries.
- Source of truth:
  - user request in this turn
  - `AGENTS.md`
  - `docs/03_quality_gates.md`
  - current frontend/backend bridge code
- Current break point / missing wiring:
  - backend result event contains only developer-oriented artifacts
  - frontend `PresentableEvent` has no dedicated delivery evidence field
  - `ResponseRenderer` compresses completion into “任务已完成，结果已准备好。”
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: project generation/delivery already produces reports, screenshots, demo media, and structured outputs.
- current_module: backend service and bridge must consolidate those artifacts into one explicit evidence manifest before the frontend renders completion.
- downstream: the frontend completion path should be able to show result summary, report path, screenshot paths, demo media paths, verification status, limitations, and next actions without scanning directories or inventing summaries.
- source_of_truth: bridge-delivered manifest, result events, and frontend rendering output.
- fallback: if a run lacks some evidence categories, emit them as empty lists/strings in the manifest and keep user-facing copy honest about what is available now.
- acceptance_test:
  - `python -m unittest tests/backend/test_backend_service.py -v`
  - `python -m unittest tests/frontend/test_frontend_handler.py -v`
  - `python -m unittest tests/test_frontend_rendering_boundary.py -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not hardcode evidence summaries in frontend copy without backend evidence input
  - do not expose only raw repo-internal paths and claim that frontend evidence display is done
  - do not rely on docs-only guidance instead of executable evidence propagation
- user_visible_effect: completion replies directly show user-facing delivery evidence and next actions instead of sending the user to inspect zip/output folders manually.

## DoD Mapping

- [x] DoD-1: Backend completion paths emit a stable delivery evidence manifest with user-facing fields including summary, view-now items, screenshots, demo media, structured outputs, verification summary, limitations, and next actions
- [x] DoD-2: Frontend result objects explicitly carry delivery evidence and completion replies render it as a user-facing evidence block instead of generic “done” text
- [x] DoD-3: Focused tests and canonical verify pass from the updated task/report state

## Acceptance

- [x] DoD written (this file complete)
- [x] Research logged (repo-local search only)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Add a first-class delivery evidence schema plus a bridge-side manifest builder/writer.
2. Thread that manifest through backend result assembly and frontend presentable events.
3. Render user-facing evidence summary in completion replies while keeping engineering/debug details secondary.
4. Add focused tests for backend evidence emission and frontend evidence rendering.
5. Run focused tests and canonical verify, then close the task with evidence.

## Check / Contrast / Fix Loop Evidence

- check-1: completion evidence currently lives in project directories, zips, and raw artifact paths, but the frontend mainline only returns a generic completion sentence.
- contrast-1: this task requires the frontend to directly surface delivery evidence without forcing the user to inspect zip/output trees manually.
- fix-1: add a backend-generated delivery evidence manifest and thread it into the completion event/result object.
- check-2: even if the backend exposes raw artifacts, the frontend can still fail this task by rendering only generic text.
- contrast-2: the reply must organize evidence around user-facing summary, what can be viewed now, verification state, and next actions.
- fix-2: add an evidence-aware renderer and dedicated result field in the frontend presentable event.
- check-3: user-facing evidence should not be polluted by developer-only detail.
- contrast-3: users should see outcome, previewable assets, and next steps first; engineering internals stay secondary/debug.
- fix-3: keep the evidence manifest user-oriented and relegate raw run/debug values to secondary artifacts rather than the primary reply.

## Completion Criteria Evidence

- connected + accumulated + consumed:
- connected: backend completion state, bridge manifest, result event, and frontend reply are wired through one evidence path.
- accumulated: screenshots, reports, demo media, structured outputs, verification summary, limitations, and next actions are normalized into one stable manifest.
- consumed: the frontend result object and completion copy consume that manifest directly instead of reconstructing delivery evidence from raw paths.

## Notes / Decisions

- Default choices made: treat bridge-side evidence assembly as backend truth for the current mainline, then serialize that into result events and frontend display blocks.
- Alternatives considered: adding evidence logic only in the frontend; rejected because it would keep the frontend guessing which outputs matter.
- Any contract exception reference:
  - None
- Issue memory decision: none; this is a scoped delivery-surface implementation task, not a recurring runtime defect class.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes` using `ctcp-workflow` for repo-standard execution and `ctcp-verify` for canonical closure.

## Results

- Files changed:
  - `contracts/schemas/delivery_evidence.py`
  - `contracts/schemas/event_result.py`
  - `scripts/project_delivery_evidence_bridge.py`
  - `scripts/ctcp_front_bridge.py`
  - `apps/project_backend/application/delivery_evidence.py`
  - `apps/project_backend/application/service.py`
  - `apps/project_backend/domain/job.py`
  - `apps/project_backend/orchestrator/job_runner.py`
  - `apps/cs_frontend/domain/presentable_event.py`
  - `apps/cs_frontend/dialogue/delivery_evidence_renderer.py`
  - `apps/cs_frontend/dialogue/response_renderer.py`
  - `apps/cs_frontend/application/handle_user_message.py`
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/ollama_agent.py`
  - `tests/backend/test_backend_service.py`
  - `tests/frontend/test_frontend_handler.py`
  - `tests/test_delivery_evidence_bridge.py`
  - `tests/test_ollama_agent.py`
  - `tests/test_provider_selection.py`
  - `tests/test_mock_agent_pipeline.py`
- Verification summary:
  - focused evidence tests passed for backend/frontend/bridge propagation
  - `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v` -> `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
