# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-07`
- Topic: `support session recovery and blocked plan self-heal`

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_support_recovery.py`
- `frontend/conversation_mode_router.py`
- `frontend/response_composer.py`
- `frontend/support_reply_policy.py`
- `frontend/recovery_visibility.py`
- `simlab/generate_s16_fix_patch.py`
- `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
- `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- `tests/test_support_bot_humanization.py`
- `tests/test_support_reply_policy_regression.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_session_recovery_regression.py`
- `tests/test_support_proactive_recovery_regression.py`
- `tests/test_support_to_production_path.py`
- `tests/test_frontend_rendering_boundary.py`
- runtime evidence under `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664\` and `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260407-090038-197327-orchestrate\`

### Plan

1. Trace the real support -> frontend -> bridge -> orchestrate call chain and confirm where stale run recovery, short-confirmation routing, and blocked plan recovery diverge.
2. Unify stale `bound_run_id` recovery across direct turns and proactive cycle so dead bindings are cleared and a recoverable visible state is written back.
3. Reuse existing project context for short confirmation turns instead of letting `ctcp_new_run(goal=user_text)` create bogus goals like `确定`.
4. Mark missing `PLAN_draft.md` as a retryable recovery state, allow planner auto-retry, and expose truthful blocker/next-step text to the customer-visible lane.
5. Add focused regressions and close with canonical verify evidence.

### Changes

- Added confirmation-turn routing in `frontend/conversation_mode_router.py` so short replies like `确定/可以/继续/ok/go on` stay on the current project lane, and route to `PROJECT_DECISION_REPLY` when the session is explicitly waiting for a decision.
- Added unified stale-run and blocked-plan recovery helpers in `scripts/ctcp_support_recovery.py`, and wired them into `scripts/ctcp_support_bot.py`:
  - stale `bound_run_id` now clears in both direct sync and proactive cycle
  - session state is rewritten into an explicit recoverable status instead of only logging
  - low-signal turns now resolve new-run goals from the saved project brief, not from raw confirmation text
- Added blocked-plan recovery semantics in `scripts/ctcp_front_bridge.py` and `scripts/ctcp_support_bot.py`:
  - missing `PLAN_draft.md` now produces retry-ready recovery metadata
  - proactive auto-advance can retry planner work for that gate
  - progress binding exposes the real blocker and recovery next action instead of generic “继续推进”
- Added `frontend/recovery_visibility.py` and moved recovery-surface extraction/rendering there so:
  - `frontend/support_reply_policy.py` classifies internal blocked/recover states as recovery instead of missing-input
  - `frontend/response_composer.py` can render truthful blocked text like `PLAN_draft.md`/next-action without regressing growth-guard
  - the frontend sanitizer still hides raw internal prompts but no longer erases the user-facing recovery blocker line
- Repaired SimLab `S16_lite_fixer_loop_pass` drift by splitting the fragile fixture logic:
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` now stays as a stable README-only policy fixture for `S19`
  - `simlab/generate_s16_fix_patch.py` now generates the second-pass fixer patch from the live sandbox state so it restores the broken README doc-index line and touches workflow meta files without depending on historical task/report headings
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml` now calls the helper instead of copying a stale static patch
- Added issue memory entry `Example 27` in `ai_context/problem_registry.md` for stale-run residue plus confirm-word misbinding.
- Added/updated regressions in:
  - `tests/test_support_bot_humanization.py`
  - `tests/test_support_reply_policy_regression.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_session_recovery_regression.py`
  - `tests/test_support_proactive_recovery_regression.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_frontend_rendering_boundary.py`

### Verify

- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
  - result: support sync, stale-run recovery, confirmation routing, and customer-visible blocked-plan wording regressions all pass
- `python -m unittest discover -s tests -p "test_support_reply_policy_regression.py" -v` -> `0`
  - result: internal recovery states no longer collapse into `ask_missing_input`, and recovery fallback text exposes the real blocker/next action
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
  - result: proactive stale-run recovery and blocked-plan auto-retry wiring pass
- `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `0`
  - result: canonical runtime snapshot now marks missing `PLAN_draft.md` as retryable recovery state
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0`
  - result: frontend routing keeps confirmation turns on the active project/decision path
- `python -m unittest discover -s tests -p "test_support_session_recovery_regression.py" -v` -> `0`
  - result: direct stale-run self-heal, confirm-turn reuse, and user-visible blocked-plan recovery phrasing all pass in focused regression form
- `python -m unittest discover -s tests -p "test_support_proactive_recovery_regression.py" -v` -> `0`
  - result: proactive stale-run self-heal and planner retry behavior pass without inflating the legacy wiring test file
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
  - result: issue-memory contract still accepts the new recurring failure entry and evidence shape
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
  - result: this task remains explicitly marked non-skillized for the correct reason, so skill-consumption contract stays green
- `python simlab/run.py --suite lite` -> `0`
  - result: final lite replay passed `14/14` at `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260407-143546` after stabilizing the S16 fixer-loop repair path
- first failure point during closure: `workflow gate (workflow checks)` during the first `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
  - reason: repo workflow gate requires `meta/reports/LAST.md` to be updated whenever code changes land, and the report still pointed to the previous GUI-removal topic
- minimal fix strategy applied: update `meta/reports/LAST.md`, stabilize S16 SimLab fixer-loop repair generation, rerun lite replay, then rerun canonical verify
- second closure fix after live Telegram retest: provider/project-detail blocked replies still degraded to “当前遇到内部阻塞，确认这条输入后我可以继续” because frontend reply policy misclassified internal recovery as missing-input, and the frontend sanitizer stripped lines containing `PLAN_draft.md`
- minimal fix strategy applied: move recovery blocker extraction/rendering into `frontend/recovery_visibility.py`, classify internal blocked states as recovery, and allow truthful `PLAN_draft.md` blocker lines while still hiding raw internal prompt labels
- final `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`
  - result: canonical code-profile verify passed, including headless build, ctest lite, workflow/plan/patch/behavior/contract/doc-index/code-health/triplet gates, lite scenario replay, and python unit tests, with growth-guard satisfied after extracting the new recovery helper module

### Questions

- None.

### Demo

- Before the patch, a dead `bound_run_id` could survive in support session state, proactive polling would keep retrying it, and the next `确定/继续` turn could create a bogus new run whose `analysis.md` goal was the confirmation word itself.
- After the patch, stale run bindings are cleared in both direct and proactive paths, short confirmation turns stay attached to the saved project brief/current run, blocked `PLAN_draft.md` states advertise a retryable recovery path, and the customer-visible reply now says the real blocker/next action instead of asking for a fake confirmation.
