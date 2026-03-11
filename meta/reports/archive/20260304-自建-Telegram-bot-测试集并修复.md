# Update 2026-03-04（自建 Telegram bot 测试集并修复）

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_support_bot_suite_v1.py`

### Plan
1) 新建数据驱动测试集（fixture + unittest），覆盖 Telegram bot 的无 run/有 run 入口行为。  
2) 跑新测试集，锁定首个失败点。  
3) 按首个失败点做最小修复（只改入口意图分流与清理意图识别）。  
4) 回归新测试 + 既有 Telegram 测试 + `scripts/verify_repo.ps1`。  

### Changes
- 新增 `tests/fixtures/telegram_bot_dataset_v1/cases.jsonl`
  - 5 个数据用例（无 run 小聊、无 run 看进度、无 run 清理、无 run 新目标、有 run 看进度）。
- 新增 `tests/fixtures/telegram_bot_dataset_v1/README.md`
  - 数据集说明。
- 新增 `tests/test_telegram_cs_bot_dataset_v1.py`
  - 数据驱动回放 `process_update`，断言 reply 与 run 绑定状态。
- 修改 `tools/telegram_cs_bot.py`
  - `is_cleanup_project_request(...)` 增加 `先清理一下` 及短句清理表达识别。
  - 无 run 分支新增意图分流：`debug/status/outbox/advance/bundle/report/decision` 不再误建 run，改为提示用户先给明确目标。

### Verify
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_dataset_v1.py" -v`（修复前）=> exit `1`
  - first failure:
    - `U02`：`查看进度`（无 run）误走新建流程
    - `U03`：`先清理一下`（无 run）未识别为 cleanup
  - minimal fix:
    - no-run 入口增加 `debug/status/...` 分流提示，不触发 `_create_run`
    - cleanup 意图补充短句识别
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_dataset_v1.py" -v`（修复后）=> exit `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（13 passed）
- `python -m unittest discover -s tests -p "test_support_bot_suite_v1.py" -v` => exit `0`（2 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-212117`（`passed=14 failed=0`）
  - python unit tests: `Ran 109 tests, OK (skipped=3)`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after report update）=> exit `0`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-212644`（`passed=14 failed=0`）
  - python unit tests: `Ran 109 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- New dataset: `tests/fixtures/telegram_bot_dataset_v1/cases.jsonl`
- New test: `tests/test_telegram_cs_bot_dataset_v1.py`
- Verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-212117/summary.json`
- Final recheck summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-212644/summary.json`

