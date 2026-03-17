# Task Archive - 2026-03-17 - Support 旧项目进度追问绑定真实 run 状态

Queue Item: `ADHOC-20260317-support-previous-project-status-grounding`
Status: `done`

## Summary

- Scoped support runtime task for the live Telegram regression where an old-project status follow-up is misrouted as `PROJECT_DETAIL`, overwrites the support brief, and triggers fresh planning/file-request work.
- Focuses on conversation-mode detection, brief preservation, and grounded status replies only.
- Requires repo evidence plus live runtime confirmation against chat `6092527664`.

## Scope

- `frontend/conversation_mode_router.py`
- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260317-support-previous-project-status-grounding.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260317-support-previous-project-status-grounding.md`

## Key Constraints

- no bridge API semantic change
- no proactive-push rollback
- no fake status-template bypass that ignores real run truth
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- old-project status follow-ups route through grounded status/progress handling
- those turns no longer overwrite the current project brief or trigger fresh planning/file-request work
- task closes with canonical verify evidence and live bot restart

## Closure

- `frontend/conversation_mode_router.py` now recognizes old-project progress wording as `STATUS_QUERY`.
- `scripts/ctcp_support_bot.py` now preserves the existing `project_brief` for this wording class and upgrades any active-run misroute back to `STATUS_QUERY`.
- Focused regressions landed in `tests/test_frontend_rendering_boundary.py` and `tests/test_support_bot_humanization.py`.
- Canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` passed, and the Telegram bot was restarted as PID `37072` at `2026-03-17 18:01:38`.
