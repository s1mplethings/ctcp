# Task Archive - 2026-03-16 - Support 主动进度推送与旧大纲恢复

Queue Item: `ADHOC-20260316-support-proactive-progress-and-resume`
Status: `doing`

## Summary

- Scoped support runtime task for the live Telegram regression where backend progress changes are not pushed proactively and explicit "continue the previous outline" requests can create a new generic run that stalls.
- Focuses on support session continuity, background run advancement/progress notification, and live Telegram runtime recovery.
- Requires both repo evidence and live runtime evidence against chat `6092527664`.

## Scope

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-support-proactive-progress-and-resume.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-support-proactive-progress-and-resume.md`
- live support session/runtime artifacts outside the repo

## Key Constraints

- no provider stack refactor
- no `ctcp_front_bridge` API semantic change
- no prompt-only proactive-update wording; runtime digest/state wiring must be real
- no manual session clearing presented as a product fix
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- active Telegram sessions can proactively push a grounded progress update when the bound run state materially changes
- eligible bound runs can auto-advance in the background when no user decision is needed
- explicit previous-outline continuation requests recover a concrete archived brief instead of binding a fresh generic run
- task closes with canonical verify evidence and a live bot restart

