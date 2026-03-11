# Update 2026-03-07 - Telegram 客服继续测试（Wave 2）

### Readlist
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `scripts/ctcp_support_bot.py`
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_support_bot_suite_v1.py`
- `tests/test_support_router_and_stylebank.py`
- `tests/test_telegram_cs_bot_dataset_v1.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `tests/test_telegram_cs_bot_intent_matrix.py`

### Plan
1) 在上一轮基础上继续扩大循环规模与压力样本量。
2) 复跑 support/telegram 回归测试集，验证稳定性。
3) 对比 `with_commands` 与 `no_commands` 压力报告，检查用户通道泄漏风险。
4) 复跑 `scripts/verify_repo.ps1`，锁定最新首个失败 gate。
5) 写入本轮证据路径与最小修复建议。

### Changes
- `meta/tasks/CURRENT.md`
  - 追加 “继续测试（Wave 2）” update 节。
- `meta/reports/LAST.md`
  - 追加本轮 Readlist/Plan/Changes/Verify/Questions/Demo。
- 业务代码改动：无（本轮仅测试与报告落盘）。

### Verify
- `python scripts/ctcp_support_bot.py --selftest`（循环 50 次，脚本化）=> exit 0
  - result: `pass=50 fail=0`
  - report: `C:\Users\sunom\.ctcp\runs\ctcp\manual_cs_tests\20260307-continue-wave2\selftest_loop_50.json`
- `$env:CTCP_SUPPORT_SUITE_PROFILE='custom:core,memory,routing,tone,safety'; python -m unittest discover -s tests -p "test_support_bot_suite_v1.py" -v` => exit 0
  - result: 2 tests passed（测试方法内部按 profile 读取 case 集）
- `python -m unittest discover -s tests -p "test_support_bot_*.py" -v` => exit 0
  - result: 16 tests passed
- `python -m unittest discover -s tests -p "test_support_router_and_stylebank.py" -v` => exit 0
  - result: 5 tests passed
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_*.py" -v` => exit 0
  - result: 19 tests passed
- Wave 2 高压回放（含命令）=> exit 0
  - summary: `total=220 empty=0 forbidden=0 multi_q_over2=0 pass=true`
  - report: `C:\Users\sunom\.ctcp\runs\ctcp\manual_cs_tests\20260307-continue-wave2\dialogue_stress_with_commands.json`
- Wave 2 高压回放（纯自然会话）=> exit 0
  - summary: `total=260 empty=0 forbidden=0 multi_q_over2=0 pass=true`
  - report: `C:\Users\sunom\.ctcp\runs\ctcp\manual_cs_tests\20260307-continue-wave2\dialogue_stress_no_commands.json`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-152314/summary.json`
  - summary: `passed=12 failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: `missing expected text: failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: `expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused):
  - S15: 对齐 S15 用例 expected text 与当前 fixer prompt 文案。
  - S16: 更新 `lite_fix_remove_bad_readme_link.patch` 使其可应用于当前 `README.md`。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Wave 2 selftest loop:
  - `C:\Users\sunom\.ctcp\runs\ctcp\manual_cs_tests\20260307-continue-wave2\selftest_loop_50.json`
- Wave 2 stress reports:
  - `C:\Users\sunom\.ctcp\runs\ctcp\manual_cs_tests\20260307-continue-wave2\dialogue_stress_with_commands.json`
  - `C:\Users\sunom\.ctcp\runs\ctcp\manual_cs_tests\20260307-continue-wave2\dialogue_stress_no_commands.json`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-152314/summary.json`
- Verify failure bundles:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-152314/S15_lite_fail_produces_bundle/failure_bundle.zip`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-152314/S16_lite_fixer_loop_pass/failure_bundle.zip`

