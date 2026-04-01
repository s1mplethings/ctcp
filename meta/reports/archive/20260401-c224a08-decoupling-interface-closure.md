# Demo Report - c224a08-decoupling-interface-closure

## Readlist

- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `scripts/ctcp_support_bot.py`
- `frontend/frontdesk_state_machine.py`
- `scripts/ctcp_support_controller.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_to_production_path.py`

## Plan

1) Add unified policy layer for reply intent + fallback rendering + anti-mechanical guard.
2) Extend policy with cross-turn dedupe memory and near-duplicate suppression.
3) Route support bot final reply output through policy+dedupe.
4) Re-run support/frontdesk/runtime boundary suites.

## Changes

- Added `frontend/support_reply_policy.py`:
  - `infer_reply_intent`
  - `render_fallback_reply`
  - `enforce_reply_policy`
  - `default_reply_dedupe_memory`
  - `normalize_reply_dedupe_memory`
- Updated `scripts/ctcp_support_bot.py`:
  - policy/dedupe import wiring
  - session-level `reply_dedupe_memory` state normalization and persistence
  - final reply doc now includes `reply_intent`, `reply_template_id`, and enriched `reply_policy` (`dedupe_action`, `similarity_max`, `suppressed`)
  - proactive path now allows dedupe suppression when no new information
  - fallback normalization keeps legacy customer-safe empty-reply wording compatibility
- Updated `tests/test_support_reply_policy_regression.py` with dedupe-focused regression tests:
  - `natural_reply_policy_test`
  - `template_id_dedupe_test`
  - `semantic_progress_dedupe_test`
  - `per_intent_bucket_test`
  - `resend_downgrade_test`
  - `decision_question_not_over_deduped_test`
  - `error_recovery_contextual_dedupe_test`
  - `transcript_near_duplicate_regression_test`
  - `provider_mode_consistency_with_dedupe_test`

## Verify

- `python -m py_compile frontend/support_reply_policy.py scripts/ctcp_support_bot.py tests/test_support_reply_policy_regression.py` -> `0`
- `python tests/test_support_reply_policy_regression.py` -> `0` (`Ran 9 tests`)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (`Ran 58 tests`)
- `python tests/test_runtime_wiring_contract.py` -> `0` (`Ran 23 tests`)
- `python tests/test_support_runtime_acceptance.py` -> `0` (`Ran 10 tests`)
- `python tests/test_support_to_production_path.py` -> `0` (`Ran 6 tests`)
- `python -m unittest discover -s tests -p "test_support_controller_boundary.py" -v` -> `0` (`Ran 3 tests`)
- `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> `0` (`Ran 6 tests`)
- first canonical verify attempt: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1` (workflow gate: missing CURRENT evidence sections)
- second canonical verify attempt: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1` (workflow gate: missing Integration Check `fallback`/`user_visible_effect`)
- third canonical verify attempt: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1` (lite replay `S16_lite_fixer_loop_pass`: fixture patch syntax/context drift)
- fix for third attempt: update `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to current `CURRENT.md` title and valid unified-diff context prefix
- final canonical verify: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0 (OK)`; lite replay `passed=14 failed=0` (`run_dir=C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260401-193701`)

## Questions

- None.

## Demo

- Unified policy layer now includes cross-turn dedupe memory and semantic near-duplicate suppression.
- Progress updates with unchanged context are downgraded/suppressed instead of repeating near-synonym status lines.
- Decision/error/result intents are deduped by intent buckets and context signatures to avoid cross-intent false suppression.
