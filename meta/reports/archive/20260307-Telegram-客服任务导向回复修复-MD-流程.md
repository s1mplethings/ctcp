# Update 2026-03-07 - Telegram 客服任务导向回复修复（MD 流程）

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
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/TEMPLATE.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `agents/prompts/support_lead_router.md`
- `agents/prompts/support_lead_reply.md`
- `docs/10_team_mode.md`
- `tools/telegram_cs_bot.py`

### Plan
1) 先更新任务绑定（Queue/CURRENT），再做 spec-first 文档与 prompt 约束更新。
2) 对 `telegram_cs_bot` 做最小行为改动：首轮/续轮分流、fallback 任务导向化、历史上下文谨慎引用。
3) 补充回归测试并执行 support/telegram 相关测试集。
4) 运行唯一 DoD 入口 `scripts/verify_repo.ps1`。
5) 记录首个失败点和最小修复策略并落盘。

### Changes
- `meta/backlog/execution_queue.json`
  - 新增 `ADHOC-20260307-support-task-oriented-dialogue` 任务项（DoD/测试命令/产物绑定）。
- `meta/tasks/CURRENT.md`
  - 新增本次 update，绑定 ADHOC 队列项并更新 DoD/Acceptance 状态。
- `agents/prompts/support_lead_reply.md`
  - 增加硬约束：禁止空泛续聊、首句任务定向、每轮至少一个具体动作、上下文引用条件化。
- `agents/prompts/support_lead_router.md`
  - 增加路由硬约束：首轮/续轮区分，`need_more_info` 必须 bounded task-entry 问题。
- `docs/10_team_mode.md`
  - 追加任务导向客服约束说明（空话禁用、任务定向、动作推进、上下文门控）。
- `tools/telegram_cs_bot.py`
  - 新增 `is_explicit_continuation_request`。
  - `detect_intent` 增强“你现在手头还有我的项目吗”这类状态识别。
  - 小聊回复去除默认“接着聊历史项目”注入（无显式续项目时不引用旧项目）。
  - `build_employee_note_reply` 改为任务入口导向（lane 选项 + 明确输入动作），移除旧机械话术。
  - `need_more_info` 与 `_fallback_support_reply` 改为任务推进口径，避免通用安抚 + 空泛追问。
  - 新建 run 首条回复不再强加默认泛问句（`next_question=""`）。
- `tests/test_telegram_cs_bot_intent_matrix.py`
  - 新增 `你现在手头还有我的项目吗 -> status` 用例。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 新增/更新任务导向文案断言与“非 generic chitchat”断言。
- `tests/test_support_bot_humanization.py`
  - 更新小聊测试，改为“非显式续项目不回放旧项目标签”的新规则。

### Verify
- `$env:PYTHONPATH='.'; python tests/test_telegram_cs_bot_intent_matrix.py` => exit 0
- `$env:PYTHONPATH='.'; python tests/test_telegram_cs_bot_employee_style.py` => exit 0
- `$env:PYTHONPATH='.'; python tests/test_support_bot_humanization.py` => exit 0
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_telegram_cs_bot_*.py" -v` => exit 0
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_support_bot_*.py" -v` => exit 0
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-165254/summary.json`
  - summary: `passed=12 failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: `missing expected text: failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: `expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused):
  - S15: 对齐 S15 断言与当前 outbox prompt 文案，补齐 `failure_bundle.zip` 关键提示文本。
  - S16: 更新 `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` 以匹配当前 `README.md` 上下文，恢复第二次 `advance` 通过。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Queue: `meta/backlog/execution_queue.json`
- Verify summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-165254/summary.json`
- Verify traces:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-165254/S15_lite_fail_produces_bundle/TRACE.md`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260307-165254/S16_lite_fixer_loop_pass/TRACE.md`

