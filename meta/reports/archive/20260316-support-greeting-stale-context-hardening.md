# Report Archive - 2026-03-16 - Support greeting 泄露旧项目/旧交付上下文硬化

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `ai_context/problem_registry.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

## Plan

1. Bind a stale greeting/project-delivery context hardening task.
2. Prevent non-project prompt construction from carrying old project/delivery context unless the latest turn explicitly requests continuation or delivery.
3. Strip delivery actions on non-project turns that did not explicitly request package/screenshot delivery.
4. Add focused regressions for prompt/action leakage.
5. Run focused tests, restart the live Telegram bot on the new code, and rerun canonical verify.

## Changes

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-support-greeting-stale-context-hardening.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-support-greeting-stale-context-hardening.md`

## Verify

- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- live runtime repair:
  - stopped old Telegram bot `PID 36556`
  - backed up stale chat session to `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664.backup-20260316-182553`
  - restarted Telegram bot as `PID 45900` at `2026-03-16 18:26:10`
  - direct `getMe` on launcher token -> `ok=true`, `username=my_t2e5s9t_bot`
  - direct `getUpdates` while bot is polling -> `HTTP 409 Conflict` (expected when another getUpdates consumer is active)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point: `PASS`
- minimal fix strategy: none
- final verify result:
  - profile: `code`
  - gates executed: `lite`, `workflow_gate`, `plan_check`, `patch_check`, `behavior_catalog_check`, `contract_checks`, `doc_index_check`, `triplet_guard`, `lite_replay`, `python_unit_tests`
  - lite replay summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-182824\summary.json`

## Questions

- None.

## Demo

- live bot process before fix: `pythonw scripts\ctcp_support_bot.py telegram --poll-seconds 2 --allowlist 6092527664`, created `2026-03-16 17:20:06`
- live session state before fix: `support_sessions\6092527664\artifacts\support_session_state.json` shows `bound_run_id=20260313-123848-141809-orchestrate`
- live session state before fix: `latest_support_context.package_ready=true`
- live reply before fix: greeting turn returned old story package wording and `send_project_package(zip)`
- live session backup after fix: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\6092527664.backup-20260316-182553`
- live bot process after fix: `PID 45900`, created `2026-03-16 18:26:10`
- canonical verify result: `[verify_repo] OK`

## Integration Proof

- upstream: user provided a real Telegram transcript showing greeting replies still leaking old project/package context.
- current_module: support-bot prompt context construction, delivery-action gating, and live runtime restart.
- downstream: Telegram visible replies, support session state, and support-bot regressions.
- source_of_truth: current `scripts/ctcp_support_bot.py`, real session artifacts under `support_sessions/6092527664`, and focused tests.
- fallback: if canonical verify fails, record only the first failing gate.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not only restart the bot without fixing the prompt/action leak
  - do not delete the whole session tree to fake a clean result
  - do not remove real delivery ability from project/status turns
- user_visible_effect: sending only `你好` in an old chat should stop triggering old project/package replies.
