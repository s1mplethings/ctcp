# Update 2026-03-02 (my_test_bot 输出去“机械重复追问”)

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `tools/telegram_cs_bot.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `meta/tasks/CURRENT.md`

### Plan
1) Docs/spec first：更新任务单与 team mode 文档，明确 blocked 去重和自动推进口径。  
2) Code：修复 `telegram_cs_bot` 在 blocked 状态的重复播报/重复追问，并避免手动 advance 后同轮二次自动推进。  
3) Tests：增加 blocked 冷却与手动 advance 行为回归测试。  
4) Verify：执行唯一验收入口 `scripts/verify_repo.ps1` 并记录 run 证据。  
5) Report：回填本节到 `meta/reports/LAST.md`。  

### Changes
- `tools/telegram_cs_bot.py`
  - 增加 blocked 状态持久化字段：`blocked_signature` / `blocked_since_ts`。
  - 新增 blocked 管理逻辑：
    - `_blocked_signature()` / `_mark_blocked_hold()` / `_clear_blocked_hold()` / `_is_blocked_hold_active()`
    - 同一 blocked 原因在冷却期（180s）内抑制重复用户播报，ops 仍写日志。
  - `advance blocked` 用户文案改为“卡点 + 需要补齐的信息 + 单问题”，去掉“继续自动推进可以吗”循环问句。
  - `_allow_auto_advance()` 接入 blocked hold：冷却期内不自动推进。
  - `_scan_push()` 增加 `allow_auto_advance` 参数；手动 `/advance`、fallback advance、API advance、failure retry 后同轮关闭二次自动推进，避免一轮两次播报。
  - 用户补充输入时清除 blocked hold（`_write_reply`、`_handle_support_turn`、`/note`）。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 新增 `test_advance_blocked_is_throttled_and_not_repeated`。
  - 新增 `test_command_advance_skips_second_auto_advance_in_same_turn`。
- `docs/10_team_mode.md`
  - 补充 blocked 去重/冷却与“补充输入后自动续推”说明。
- `meta/tasks/CURRENT.md`
  - 追加本次任务 update 与 DoD/Acceptance。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py` => exit `0`
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（13 passed）
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（3 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=11`)
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-191930`（`passed=14 failed=0`）
  - python unit tests: `Ran 89 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Ops log (run_dir): `logs/telegram_cs_bot.ops.jsonl`（可见 `advance_blocked_suppressed` 记录）
- Verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-191930/summary.json`

