# Report Archive - 2026-03-17 - Support 主动推送误复用寒暄修复

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `docs/11_task_progress_dialogue.md`
- `PATCH_README.md`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

## Plan

1. Bind a narrow proactive-push greeting-dup task.
2. Force proactive push rendering to use status/progress semantics instead of the latest greeting.
3. Add a focused regression.
4. Run canonical verify and restart the live bot.

## Changes

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260317-support-proactive-push-greeting-dup-guard.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260317-support-proactive-push-greeting-dup-guard.md`

## Verify

- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` via canonical verify
- first failure point: live runtime first failure is proactive push reusing the latest greeting and reclassifying the push into `UNDERSTOOD/GREETING`
- minimal fix strategy: inject an explicit status/progress latest-turn override into the proactive push render path, then rerun canonical verify and live bot restart
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- final verify result:
  - profile: `code`
  - gates executed: `lite`, `workflow_gate`, `plan_check`, `patch_check`, `behavior_catalog_check`, `contract_checks`, `doc_index_check`, `triplet_guard`, `lite_replay`, `python_unit_tests`
  - lite replay summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260317-170045\summary.json`

## Questions

- None.

## Demo

- live evidence before fix:
  - one inbound greeting in `support_inbox.jsonl`
  - one later `SUPPORT_PROGRESS_PUSHED` event
  - one duplicate greeting-like `support_runtime` reply
- focused regression proof:
  - `test_build_grounded_status_reply_doc_does_not_repeat_latest_greeting`
- live runtime restart after fix:
  - restarted Telegram bot `PID 26304`, created `2026-03-17 16:59:35`
