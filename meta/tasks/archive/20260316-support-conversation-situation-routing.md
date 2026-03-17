# Task Archive - 2026-03-16 - Support 对话场景先分流再回复

Queue Item: `ADHOC-20260316-support-conversation-situation-routing`
Status: `done`

## Summary

- Scoped support-lane task for the user's request to identify the current conversation situation first, handle greeting separately, and answer different content for different situations.
- Focuses on shared router/composer/support-bot behavior rather than Telegram auth, provider connectivity, or orchestrator runtime changes.
- Requires code, contract, regression, and canonical verify evidence in one patch.

## Scope

- `frontend/conversation_mode_router.py`
- `frontend/response_composer.py`
- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-support-conversation-situation-routing.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-support-conversation-situation-routing.md`

## Key Constraints

- no Telegram token/auth work
- no orchestrator/scaffold/provider-path refactor
- no prompt-only completion; shared routing and regressions must change together
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- greeting, capability, project-like, and status turns are differentiated before reply emission
- customer-facing entry replies differ by situation instead of reusing one generic shell
- focused support/frontend regressions cover the new split
- task closes with canonical verify evidence
