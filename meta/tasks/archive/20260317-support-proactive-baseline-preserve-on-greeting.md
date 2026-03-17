# Task Archive - 2026-03-17 - Support greeting turn 保留主动进度基线

Queue Item: `ADHOC-20260317-support-proactive-baseline-preserve-on-greeting`
Status: `done`

## Summary

- Scoped support runtime task for the live Telegram regression where a greeting turn overwrites the last real proactive-progress digest and causes a same-state progress push immediately afterward.
- Focuses on proactive-progress baseline preservation only.
- Requires repo evidence plus live runtime confirmation against chat `6092527664`.

## Scope

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260317-support-proactive-baseline-preserve-on-greeting.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260317-support-proactive-baseline-preserve-on-greeting.md`

## Key Constraints

- no proactive-push rollback
- no bridge API semantic change
- no greeting-to-status visible behavior leak
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- greeting turns no longer reset the real proactive-progress baseline
- greeting + same-state proactive push regression is covered
- task closes with canonical verify evidence and live bot restart

## Closure

- `remember_progress_notification()` now returns early unless a real `project_context.run_id` is present.
- Focused regression `test_process_message_greeting_does_not_reset_real_progress_digest` landed in `tests/test_support_bot_humanization.py`.
- Canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` passed and the Telegram bot was restarted on the repaired runtime.
