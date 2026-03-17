# Report Archive - 2026-03-17 - Support 旧项目进度追问绑定真实 run 状态

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
- `frontend/conversation_mode_router.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_support_bot_humanization.py`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

## Plan

1. Bind a narrow previous-project status-grounding task.
2. Route old-project progress follow-ups into the grounded status path and preserve the existing project brief.
3. Add focused regressions for routing and brief preservation.
4. Run canonical verify and restart the live bot.

## Changes

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

## Verify

- `python -m py_compile frontend\conversation_mode_router.py scripts\ctcp_support_bot.py tests\test_frontend_rendering_boundary.py tests\test_support_bot_humanization.py` -> `0`
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` via canonical verify
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` via canonical verify
- first failure point: live runtime currently routes `我想要知道我之前那个项目做成什么样子了` as `PROJECT_DETAIL`, overwrites the support brief, and asks for fresh planning docs
- minimal fix strategy: teach the router/runtime to treat old-project progress follow-ups as `STATUS_QUERY` and stop them from refreshing the bound project brief, then rerun canonical verify and live bot restart
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- final verify result:
  - profile: `code`
  - lite replay summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260317-180318\summary.json`

## Questions

- None.

## Demo

- live evidence before fix:
  - `2026-03-17T09:41:01Z` inbound `我想要知道我之前那个项目做成什么样子了`
  - `support_reply.json` returned a planning-doc question
  - `support_session_state.json.task_summary` and `project_memory.project_brief` were overwritten by the status follow-up
  - `support_whiteboard.json` appended `chair/file_request` and `librarian/context_pack`
- focused regression proof:
  - `test_previous_project_status_followup_routes_to_status_query`
  - `test_detect_conversation_mode_treats_previous_project_progress_followup_as_status_query`
  - `test_build_final_reply_doc_grounds_previous_project_status_followup`
- live runtime after fix:
  - restarted Telegram bot `PID 37072`, created `2026-03-17 18:01:38`
  - `getMe` returned `ok=true` for `@my_t2e5s9t_bot`
