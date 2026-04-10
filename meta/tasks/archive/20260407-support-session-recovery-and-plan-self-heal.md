# Task - support-session-recovery-and-plan-self-heal

## Queue Binding

- Queue Item: `ADHOC-20260407-support-session-recovery-and-plan-self-heal`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: the live Telegram/support lane is stuck behind stale run residue, confirmation-turn misbinding, and blocked plan status that does not self-heal.
- Dependency check: `ADHOC-20260406-support-delivery-evidence-surface` = `done`; `ADHOC-20260407-remove-legacy-gui-lane` = `done`.
- Scope boundary: fix support/frontend/backend session recovery and blocked-plan visibility for the existing CTCP mainline without widening into unrelated generation/runtime refactors.

## Task Truth Source

- task_purpose: repair the support/customer-visible execution lane so stale bound runs self-heal, short confirmation turns do not create bogus runs, and blocked `PLAN_draft.md` states enter a real recoverable path with truthful visible status.
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_recovery.py`
  - `frontend/conversation_mode_router.py`
  - `frontend/response_composer.py`
  - `frontend/support_reply_policy.py`
  - `frontend/recovery_visibility.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_session_recovery_regression.py`
  - `tests/test_support_proactive_recovery_regression.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `tests/test_support_reply_policy_regression.py`
  - `simlab/generate_s16_fix_patch.py`
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260407-remove-legacy-gui-lane.md`
  - `meta/reports/archive/20260407-remove-legacy-gui-lane.md`
- forbidden_goal_shift:
  - do not replace the CTCP bridge/state machine with a new support architecture
  - do not widen into unrelated project-generation or delivery-package changes
  - do not paper over the bug with prompt-only wording while leaving stale state semantics unchanged
- in_scope_modules:
  - support session state load/save/recovery
  - frontend conversation-mode routing for short confirmation/status follow-ups
  - bridge-backed run create/bind/advance logic used by support
  - customer-visible progress rendering for blocked or recoverable run states
  - focused regression coverage for stale run recovery and blocked plan self-heal
- out_of_scope_modules:
  - unrelated generated projects or scaffold/package output semantics
  - unrelated verify/build/doc cleanup
  - non-support UI/product wording beyond truthful blocked/recovery state exposure
- completion_evidence: stale `bound_run_id` residue self-heals in both direct and proactive paths, short confirmation turns reuse context instead of creating `goal=确定` runs, blocked `PLAN_draft.md` states become visible recoverable status with next action, focused regressions pass, and canonical verify closes.

## Analysis / Find

- Entrypoint analysis: support turns enter through `process_message()`, then `detect_conversation_mode()` -> `sync_project_context()` -> bridge helpers (`ctcp_new_run`, `ctcp_record_support_turn`, `ctcp_advance`, `ctcp_get_support_context`) -> frontdesk/render path; proactive status goes through `run_proactive_support_cycle()`.
- Downstream consumer analysis: the customer-visible support lane must bind to one authoritative run and surface real backend blockage/recovery, otherwise Telegram users see frozen or misleading progress.
- Source of truth:
  - user diagnosis request and explicit repair scope in this turn
  - `AGENTS.md`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `frontend/conversation_mode_router.py`
  - existing support/runtime/frontend regressions under `tests/`
- Current break point / missing wiring:
  - direct-turn sync clears stale `bound_run_id` on `run_id not found`, but proactive cycle only logs and keeps retrying the dead run
  - `sync_project_context()` still creates a new run whenever `bound_run_id` is empty and the mode is non-status, so short confirmations like `确定` can become a bogus new goal
  - blocked runs waiting for `PLAN_draft.md` stay in a long-lived blocked state without explicit recovery evidence or self-heal trigger, and support wording can degrade to generic “继续推进”
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: Telegram/support intake must either bind to an existing valid run or create a new run only for a real project goal.
- current_module: support bot, front bridge, and frontend routing/rendering must agree on when a message is a new goal, a continue turn, a status query, or a recovery step.
- downstream: proactive push, user-visible progress rendering, and backend orchestration status must show the same blocker/recovery semantics.
- source_of_truth: `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, `frontend/conversation_mode_router.py`, runtime session state, and run runtime-state artifacts.
- fallback: when a stored run is gone or planner output is missing, clear stale binding, record a recoverable state, and either resume an existing context or expose the blocked reason instead of pretending active progress.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_session_recovery_regression.py" -v`
  - `python -m unittest discover -s tests -p "test_support_proactive_recovery_regression.py" -v`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not keep a stale `bound_run_id` in session state after `run_id not found`
  - do not allow a short confirmation turn to call `ctcp_new_run()` when a valid task context already exists
  - do not keep blocked `PLAN_draft.md` states in silent `AUTO_ADVANCE_READY` with only optimistic customer-facing text
- user_visible_effect: Telegram/support users can continue a real project run without bogus rebinds, and blocked/recovery states show truthful status with next action instead of generic continue text.

## DoD Mapping

- [x] DoD-1: Support session binding self-heals consistently across direct turns and proactive cycle when a stored bound_run_id no longer resolves, and stale run residue no longer keeps polluting the chat state
- [x] DoD-2: Short confirmation or continue turns with existing project context do not create a fresh run or write a low-signal goal like `确定`; they reuse or advance the existing run instead
- [x] DoD-3: Runs blocked on missing `PLAN_draft.md` surface a real recoverable status with recovery evidence/next action, and focused support/frontend regressions plus canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` pass

## Acceptance

- [x] DoD written (this file complete)
- [x] Research logged (repo-local search only)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Trace the exact decision path for new-run, continue-run, status-query, and proactive-cycle recovery in support/frontend/bridge code.
2. Unify stale `bound_run_id` recovery so both direct and proactive paths clear dead bindings and enter a recoverable visible state.
3. Tighten confirmation/continue routing so existing project context prevents bogus new-run creation and low-signal goals like `确定`.
4. Add blocked-plan self-heal/recovery evidence and make customer-visible status reflect the real blocker/next action.
5. Add focused regressions for stale run recovery, confirmation turns, wrong-goal prevention, and blocked-plan truth, then run canonical verify.

## Check / Contrast / Fix Loop Evidence

- check-1: direct support sync and proactive polling treated `run_id not found` differently, so stale `bound_run_id` could be cleared in one path but keep polluting the other.
- contrast-1: the same dead run residue must clear in both entrypaths, otherwise session state and customer-visible progress diverge.
- fix-1: added one shared stale-run recovery helper, called from interactive sync, proactive cycle, and Telegram post-reply context fetch.
- check-2: low-signal confirmation turns like `确定/继续/开始` could hit the “no bound run + non-status” branch and call `ctcp_new_run(goal=user_text)`.
- contrast-2: if the session already has a saved project brief or active run, short confirmations must continue that context rather than become a new goal.
- fix-2: route short confirmations back onto the project lane and resolve new-run goals from the saved project brief/current context instead of the confirmation token.
- check-3: missing `PLAN_draft.md` only surfaced as a long-lived blocked gate with optimistic progress wording.
- contrast-3: blocked planner output needs a concrete recovery branch, retry path, and truthful customer-visible blocker/next-action text.
- fix-3: mark missing `PLAN_draft.md` as retry-ready recovery in runtime state, allow planner auto-retry, and feed recovery hints into progress binding/rendering.

## Completion Criteria Evidence

- connected + accumulated + consumed:
- connected: support bot session sync, proactive polling, bridge runtime snapshots, and frontend mode routing now share the same stale-run recovery and short-confirmation semantics.
- accumulated: the patch stores recoverable stale-run context, retry-ready planner recovery metadata, and focused regression coverage in one scoped task without widening into unrelated generation/runtime paths.
- consumed: direct-turn, proactive, bridge-runtime, and frontend-rendering tests all consume the new recovery semantics; canonical verify only needs the final task-card/report state to close.

## Notes / Decisions

- Default choices made: fix the state/recovery source of truth in the support lane instead of masking the bug with reply-only fallback wording.
- Alternatives considered: only clear stale run IDs in the outer Telegram loop; rejected because direct-turn sync and proactive sync would still diverge.
- Any contract exception reference:
  - None
- Issue memory decision: record this as a recurring user-visible support/runtime defect class in `ai_context/problem_registry.md`.
- Skill decision (`skillized: no, because ...`): `skillized: no, because this is a scoped repair of existing support/bridge runtime behavior, not a reusable workflow asset with stable independent inputs/outputs.`

## Results

- Files changed:
  - `frontend/conversation_mode_router.py`
  - `frontend/recovery_visibility.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_recovery.py`
  - `simlab/generate_s16_fix_patch.py`
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_session_recovery_regression.py`
  - `tests/test_support_proactive_recovery_regression.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `ai_context/problem_registry.md`
  - `meta/reports/LAST.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_session_recovery_regression.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_proactive_recovery_regression.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
  - `python simlab/run.py --suite lite` -> `0` (`run_dir=C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260407-143546`, `passed=14`, `failed=0`)
  - first canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `1` because `meta/reports/LAST.md` still pointed to the previous topic; fixed by updating this task/report state before the final rerun
  - final canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
