# Update 2026-03-03 (my_test_bot 执行目标对齐：让 bot 持续知道“要干什么”)

### Goal
- 按用户要求增强“任务感知”：让 bot 在每轮都明确当前目标和下一步动作，减少上下文漂移。

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `docs/00_CORE.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `docs/10_team_mode.md`
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_telegram_cs_bot_employee_style.py`

### Plan
1) 在会话状态新增 `execution_goal/execution_next_action`，形成稳定执行焦点。  
2) 更新状态写入规则：真实需求更新执行焦点；寒暄不污染。  
3) 在 reply prompt 注入 `execution_focus`，约束模型每轮围绕“目标+下一步”。  
4) 补最小单测并运行 `scripts/verify_repo.ps1`。  

### Changes
- `tools/telegram_cs_bot.py`
  - 新增 `_next_action_from_goal(...)`，将目标文本映射为可执行下一步动作。
  - `support_session_state.json` 新增字段：
    - `execution_goal`
    - `execution_next_action`
  - `smalltalk_reply(...)` 读取主题时优先 `execution_goal`，并继续保留寒暄伪主题过滤。
  - `_update_support_session_state(...)`：
    - 仅在非寒暄输入时更新执行焦点；
    - 生成并持久化 `execution_next_action`；
    - 避免寒暄污染 `execution_goal/user_goal`。
  - `_build_support_reply_prompt(...)` 注入：
    - `execution_focus.goal`
    - `execution_focus.next_action`
- `tests/test_support_bot_humanization.py`
  - 扩展 `test_smalltalk_does_not_set_user_goal_but_real_request_can_set`，新增执行焦点断言。
  - 新增 `test_reply_prompt_contains_execution_focus`。
- `docs/10_team_mode.md`
  - 文档补充 `execution_focus` 契约说明（目标 + 下一步动作）。
- `meta/tasks/CURRENT.md`
  - 新增本次任务节与 DoD/Acceptance。
- `meta/reports/LAST.md`
  - 新增本节审计记录。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py tests/test_support_bot_humanization.py tests/test_telegram_cs_bot_employee_style.py` => exit `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（9 passed）
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（14 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=12`)
  - contract checks: ok
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-003732`（`passed=14 failed=0`）
  - python unit tests: `Ran 96 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Task: `meta/tasks/CURRENT.md`
- Report: `meta/reports/LAST.md`
- Key implementation: `tools/telegram_cs_bot.py`
- Tests: `tests/test_support_bot_humanization.py`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-003732/summary.json`

