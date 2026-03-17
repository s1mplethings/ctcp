# Report Archive - 2026-03-17 - Support greeting turn 保留主动进度基线

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

1. Bind a narrow proactive-baseline preservation task.
2. Stop greeting/non-project turns from overwriting the last real proactive-progress digest.
3. Add a focused regression.
4. Run canonical verify and restart the live bot.

## Changes

- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260317-support-proactive-baseline-preserve-on-greeting.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260317-support-proactive-baseline-preserve-on-greeting.md`

## Verify

- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` via canonical verify
- first failure point: live runtime first failure is greeting/non-project turn overwriting `notification_state.last_progress_hash` with a synthetic empty-context digest
- minimal fix strategy: only update proactive-progress baseline when `project_context.run_id` exists, then rerun canonical verify and live bot restart
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- final verify result:
  - profile: `code`
  - lite replay summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260317-171659\summary.json`

## Questions

- None.

## Demo

- live evidence before fix:
  - one inbound greeting in `support_inbox.jsonl`
  - one later `SUPPORT_PROGRESS_PUSHED` event with no real digest change
- focused regression proof:
  - `test_process_message_greeting_does_not_reset_real_progress_digest`
- live runtime restart after fix:
  - restarted Telegram bot `PID 50008`, created `2026-03-17 17:26:25`
