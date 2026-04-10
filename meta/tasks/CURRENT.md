# Task - real-visual-evidence-and-public-delivery

## Queue Binding

- Queue Item: `ADHOC-20260410-real-visual-evidence-and-public-delivery`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: the real Telegram-bound run `20260409-215339-177800-orchestrate` is no longer blocked on generation truth. It now proves a narrower delivery gap: the generation chain can reach `verify PASS`, but GUI/web outputs still leave `visual_evidence_status=placeholder_only`, no real screenshot artifacts are surfaced, and the Telegram-facing final result can end with artifact hints instead of a real zip plus screenshot delivery record.
- Dependency check: `ADHOC-20260410-project-generation-launcher-syntax-fix` = `done`.
- Scope boundary: repair the post-generation delivery chain only. Add real screenshot evidence for GUI/web project outputs, make verify-pass delivery send actual package/photo files, and keep invalid or placeholder-only artifacts from counting as successful delivery. Do not reopen watchdog/state-machine architecture in this patch.

## Task Truth Source (single source for current task)

- task_purpose:
  - add a real screenshot capture step for `gui_first` / `web_first` generated projects after the runtime probes actually launch/export the generated output
  - persist screenshot artifacts under the generated project or run artifacts and propagate them into `source_generation_report.json`, `project_manifest.json`, and delivery evidence
  - ensure Telegram/public delivery emits real zip and screenshot files and records them in `support_public_delivery.json`
  - prove the back-half flow with focused tests and one real Telegram-lane delivery send
- allowed_behavior_change:
  - `tools/providers/project_generation_source_helpers.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `scripts/project_generation_gate.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_support_public_delivery_state.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_support_proactive_delivery.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- in_scope_modules:
  - GUI/web source-generation visual evidence capture
  - manifest/report propagation for screenshot evidence
  - verify-pass delivery action synthesis and file send plan
  - focused delivery regressions and one live Telegram delivery evidence run
- out_of_scope_modules:
  - watchdog/front-bridge/recovery truth redesign
  - provider/router refactors unrelated to delivery evidence
  - weakening any result/verify gate to tolerate placeholder-only evidence
- forbidden_goal_shift:
  - do not mark `visual_evidence_status=provided` unless a real image file is produced from the launched/exported output path
  - do not treat `placeholder_only` as delivery complete
  - do not replace file delivery with hash-only or path-only text
  - do not claim a Telegram delivery success without an updated `support_public_delivery.json`
- completion_evidence:
  - GUI/web generation tests show screenshot files exist and `visual_evidence_status` is no longer `placeholder_only`
  - support delivery tests show zip + screenshot records populate `support_public_delivery.json`
  - a real Telegram-lane outbound delivery writes `deliveries` and `sent` entries for actual files
  - canonical verify passes

## Analysis / Find (before plan)

- Entrypoint analysis:
  - `tools/providers/project_generation_source_helpers.py::build_runtime_checks()` currently launches the generated project for startup/export probes, but it does not capture any visual evidence and still allows `placeholder_only` in result gating.
  - `tools/providers/project_generation_artifacts.py::normalize_source_generation()` and `normalize_project_manifest()` propagate `visual_evidence_status` from static contract defaults instead of computed screenshot truth.
  - `scripts/project_generation_gate.py` currently accepts `placeholder_only` for GUI/web source-generation + manifest gates.
  - `scripts/ctcp_support_bot.py::collect_public_delivery_state()` and `emit_public_delivery()` can consume screenshots and zip packages, but the final reply path can still end with hash hints when no delivery actions are synthesized.
- Source of truth:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `docs/00_CORE.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `tools/providers/project_generation_source_helpers.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `scripts/project_generation_gate.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_support_public_delivery_state.py`
  - `tests/test_support_bot_humanization.py`
- Live evidence captured before edits:
  - run: `%LOCALAPPDATA%\\ctcp\\runs\\ctcp\\20260409-215339-177800-orchestrate`
  - [project_manifest.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260409-215339-177800-orchestrate/artifacts/project_manifest.json) still declares:
    - `visual_evidence_required = true`
    - `screenshot_required = true`
    - `visual_evidence_status = placeholder_only`
  - [support_public_delivery.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/artifacts/support_public_delivery.json) is empty:
    - `deliveries = []`
    - `sent = []`
  - [support_reply.json](C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/artifacts/support_reply.json) final delivery text used `artifact_hint_added` rather than real file actions.
- Repo-local + runtime evidence sufficient: `yes`

## Integration Check (before implementation)

- upstream:
  - `tools/providers/project_generation_decisions.py`
  - generated launcher scripts under `tools/providers/project_generation_business_templates.py` and `tools/providers/project_generation_generic_archetypes.py`
- current_module:
  - `tools/providers/project_generation_source_helpers.py`
  - `tools/providers/project_generation_artifacts.py`
  - `scripts/project_generation_gate.py`
  - `scripts/ctcp_support_bot.py`
- source_of_truth:
  - `tools/providers/project_generation_artifacts.py::normalize_source_generation()`
  - `scripts/project_generation_gate.py`
  - `scripts/ctcp_support_bot.py::collect_public_delivery_state()`
  - `scripts/ctcp_support_bot.py::build_final_reply_doc()`
  - `scripts/ctcp_support_bot.py::emit_public_delivery()`
- downstream:
  - `artifacts/source_generation_report.json`
  - `artifacts/project_manifest.json`
  - `artifacts/deliverable_index.json`
  - `artifacts/support_public_delivery.json`
  - Telegram-visible final delivery reply
- fallback:
  - if real screenshot capture fails for a generated GUI/web project, the gate should block with explicit visual evidence failure instead of silently leaving `placeholder_only`
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python -m unittest discover -s tests -p "test_support_public_delivery_state.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not mark delivery ready when screenshot or zip file does not physically exist
  - do not leave final Telegram delivery at hash-only artifact hints
  - do not bypass canonical verify
- user_visible_effect:
  - GUI/web projects should surface real screenshot evidence and the final Telegram result should send a usable zip plus screenshot instead of only text hints

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (delivery gap + live evidence captured)
- [x] Code changes allowed (scoped generator/delivery/tests/meta only)
- [x] Patch scope aligned with user request
- [ ] `scripts/verify_repo.*` passes
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Add a real visual evidence capture step after GUI/web runtime probes and propagate the resulting screenshot truth into source-generation reports and manifests.
2. Tighten GUI/web gates so `placeholder_only` no longer counts as a successful source-generation/manifest result.
3. Make the Telegram final delivery path auto-synthesize and send zip/screenshot files when verify-pass delivery truth exists.
4. Add focused regressions for screenshot generation, delivery manifest population, and final delivery reply actions.
5. Exercise one real Telegram-lane outbound delivery and run canonical verify.

## Check / Contrast / Fix Loop Evidence

- check-1: generation runtime probes launch/export the generated project, but no screenshot artifact is produced, so visual evidence stays `placeholder_only`.
- contrast-1: the user asked for true screenshots and real package delivery, not placeholder evidence or hash-only delivery hints.
- fix-1: capture a real image artifact from launched/exported GUI/web output and propagate it as delivery truth.
- check-2: support delivery can already send package/photo files when actions exist, but the final delivery reply can still omit those actions and only mention artifact hints.
- contrast-2: the user asked for Telegram final delivery to prioritize actual zip/screenshots.
- fix-2: synthesize concrete delivery actions from verify-pass truth and persist them in `support_public_delivery.json`.

## Completion Criteria Evidence

- connected + accumulated + consumed:
- connected: source-generation screenshot capture, manifest truth, and support delivery all point to the same actual files.
- accumulated: focused tests and runtime artifacts show screenshot existence, zip existence, and support delivery manifest contents.
- consumed: a real Telegram-lane outbound delivery uses the produced screenshot/package files and records them in `support_public_delivery.json`.

## Notes / Decisions

- Default choices made: keep the existing live Telegram session `6092527664` and the bound run `20260409-215339-177800-orchestrate` as the delivery evidence target rather than inventing a fake transport.
- Alternatives considered: fix only support reply wording or relax `placeholder_only` gate acceptance; rejected because neither would produce real visual evidence or usable delivery files.
- Any contract exception reference: none.
- Issue memory decision: yes; record “verify-pass generated project lacks screenshot/package delivery evidence even though support can consume such files” as a user-visible delivery regression if this lands cleanly.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because this patch is a CTCP-local generator/delivery repair tightly coupled to the repo’s project-generation and Telegram support contracts rather than a reusable workflow asset.`
