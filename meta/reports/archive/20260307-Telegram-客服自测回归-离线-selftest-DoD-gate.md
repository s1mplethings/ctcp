# Update 2026-03-07 - Telegram 客服自测回归（离线 selftest + DoD gate）

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

### Plan
1) 按契约完成必读清单与任务门禁确认。
2) 执行 Telegram 客服脚本离线自测（`--selftest`）。
3) 执行客服相关 Python 回归测试（support + telegram）。
4) 执行唯一 DoD 验收入口 `scripts/verify_repo.ps1`。
5) 记录首个失败点、证据路径与最小修复建议。

### Changes
- `meta/tasks/CURRENT.md`
  - 追加本次“Telegram 客服自测”更新段，记录 DoD/Acceptance/Plan。
- `meta/reports/LAST.md`
  - 追加本次 Readlist/Plan/Changes/Verify/Questions/Demo 报告。
- 业务代码变更：无（本次仅执行测试与报告落盘）。

### Verify
- `python scripts/ctcp_support_bot.py --selftest` => exit 0
  - result: PASS
  - run_dir: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\selftest-1772864344`
- `python -m unittest discover -s tests -p "test_support_*.py"` => exit 0
  - result: Ran 21 tests, OK
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_*.py"` => exit 0
  - result: Ran 19 tests, OK
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failure gate: `lite scenario replay`
  - summary: `passed=12 failed=2`
  - summary file: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-141953/summary.json`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`
      - error: `include assertion failed: missing expected text: failure_bundle.zip`
      - trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-141953/S15_lite_fail_produces_bundle/TRACE.md`
    - `S16_lite_fixer_loop_pass`
      - error: `expect_exit mismatch, rc=1, expect=0`
      - second advance tail: `blocked: patch-first gate rejected diff.patch`
      - trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-141953/S16_lite_fixer_loop_pass/TRACE.md`
- Minimal repair strategy (first-failure focused):
  - S15: 对齐 S15 用例断言与当前 outbox prompt 文案（或在 fixer prompt 显式补回 `failure_bundle.zip` 引导语）。
  - S16: 对齐 `lite_fix_remove_bad_readme_link.patch` 与当前 `README.md` 上下文，确保第二次 `advance` 可成功应用修复补丁。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Selftest run: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\support_sessions\selftest-1772864344`
- Verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-141953/summary.json`
- Failure bundles:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-141953/S15_lite_fail_produces_bundle/failure_bundle.zip`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-141953/S16_lite_fixer_loop_pass/failure_bundle.zip`

