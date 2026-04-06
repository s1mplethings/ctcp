# Task Archive - 2026-03-16 - Support greeting 泄露旧项目/旧交付上下文硬化

Queue Item: `ADHOC-20260316-support-greeting-stale-context-hardening`
Status: `done`

## Summary

- Scoped support-lane task for a real Telegram regression where greeting turns in an old chat still referenced an old story project and zip delivery.
- Focuses on `ctcp_support_bot` prompt/action gating plus a live runtime restart.
- Requires both repo evidence and runtime confirmation against the actual chat session.

## Scope

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-support-greeting-stale-context-hardening.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-support-greeting-stale-context-hardening.md`
- live support session/runtime artifacts outside the repo

## Key Constraints

- no provider stack refactor
- no Telegram token/allowlist policy change
- no prompt-only fix; prompt gating, action gating, tests, and runtime restart must all align
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- greeting/smalltalk/capability turns no longer inherit stale project/package context by default
- non-requested package delivery actions are stripped on non-project turns
- the live Telegram bot is restarted on the new code and the stale chat state is reset for retest
- task closes with canonical verify evidence
