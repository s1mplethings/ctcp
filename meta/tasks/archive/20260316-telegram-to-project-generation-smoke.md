# Task Archive - 2026-03-16 - Telegram 测试到项目生成 smoke 联通与启动检查

Queue Item: `ADHOC-20260316-telegram-to-project-generation-smoke`
Status: `done`

## Summary

- Operational smoke task for the user's request to go from Telegram testing to project generation and start what can be started safely.
- Validates the support-bot local path, real run binding, scaffold generation, and live Telegram startup status.
- Stops at evidence capture; no runtime or product repair is in scope.

## Scope

- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-telegram-to-project-generation-smoke.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-telegram-to-project-generation-smoke.md`
- external run/session/scaffold artifacts only

## Key Constraints

- no code, docs, test, or script edits
- start only safe runtime entrypoints and stop failed live processes
- canonical `verify_repo.ps1` still has to be executed and recorded

## Acceptance

- support selftest passes
- local project-intake smoke binds a real run and records its current gate
- scaffold generates an external project and its generated verify exits `0`
- live Telegram startup attempt records the first blocker instead of claiming success
- task closes with canonical verify evidence
