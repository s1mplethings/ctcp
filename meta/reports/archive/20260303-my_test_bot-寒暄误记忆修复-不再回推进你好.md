# Update 2026-03-03 (my_test_bot 寒暄误记忆修复：不再回“推进你好”)

### Goal
- 修复用户首句寒暄（如“你好”）后 bot 错把寒暄当主题回显的问题。

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
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_telegram_cs_bot_employee_style.py`

### Plan
1) 根因修复：寒暄文本不写 `user_goal`。  
2) 防御兜底：`smalltalk_reply` 若检测到主题本身是寒暄词则忽略。  
3) 新增回归测试：锁定“寒暄不写目标 + 正常诉求可写目标”。  
4) 运行 `scripts/verify_repo.ps1` 全门禁确认。  

### Changes
- `tools/telegram_cs_bot.py`
  - `smalltalk_reply(...)` 增加伪主题过滤：`topic_hint` 为寒暄词时不回显为“正在推进xxx”。
  - `_update_support_session_state(...)` 调整 `user_goal` 写入条件：
    - 寒暄输入不写入 `user_goal`；
    - 若旧 `user_goal` 为寒暄词，后续收到真实诉求时可被真实目标替换。
- `tests/test_support_bot_humanization.py`
  - 新增 `test_smalltalk_reply_ignores_trivial_topic_hint`。
  - 新增 `test_smalltalk_does_not_set_user_goal_but_real_request_can_set`。
- `meta/tasks/CURRENT.md`
  - 新增本次修复任务节（DoD/Acceptance）。
- `meta/reports/LAST.md`
  - 新增本节审计记录。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py tests/test_support_bot_humanization.py` => exit `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（8 passed）
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（14 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=12`)
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-000442`（`passed=14 failed=0`）
  - python unit tests: `Ran 95 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Task: `meta/tasks/CURRENT.md`
- Report: `meta/reports/LAST.md`
- Key fix: `tools/telegram_cs_bot.py`
- Added tests: `tests/test_support_bot_humanization.py`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-000442/summary.json`

