# Task Archive - 2026-03-17 - Support 主动推送误复用寒暄修复

Queue Item: `ADHOC-20260317-support-proactive-push-greeting-dup-guard`
Status: `doing`

## Summary

- Scoped support runtime task for the live Telegram regression where proactive push incorrectly reuses the latest greeting and emits a duplicate greeting-like reply.
- Focuses on proactive push rendering semantics only.
- Requires repo evidence plus live runtime confirmation against chat `6092527664`.

## Scope

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260317-support-proactive-push-greeting-dup-guard.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260317-support-proactive-push-greeting-dup-guard.md`

## Key Constraints

- no proactive-push rollback
- no bridge API semantic change
- no second customer-visible template stack
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- proactive push no longer reuses latest greeting semantics
- latest greeting + proactive push regression is covered
- task closes with canonical verify evidence and live bot restart

