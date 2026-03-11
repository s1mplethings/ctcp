# Update 2026-03-02 (my_test_bot 双通道去机械化)

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `tools/telegram_cs_bot.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `meta/tasks/CURRENT.md`

### Plan
1) 仅定位并修改 my_test_bot（`tools/telegram_cs_bot.py`）对话输出链路。
2) 引入 `reply_text/next_question/ops_status` 双通道与用户输出净化器。
3) 增加显式进度开关（`查看进度`/`debug`/`/debug` + env `CTCP_TG_PROGRESS_PUSH`）。
4) 增补最小单测并跑 `verify_repo`。

### Changes
- `tools/telegram_cs_bot.py`
  - 新增用户回复双通道 payload：
    - `build_user_reply_payload(reply_text,next_question,ops_status)`
    - `sanitize_customer_reply_text(...)`
  - 新增统一发送入口 `_send_customer_reply(...)`：
    - 用户只收净化后的三段式文本
    - `ops_status` 写入 `run_dir/logs/telegram_cs_bot.ops.jsonl`
  - 新增内部事件里程碑映射：
    - `guardrails_written -> 已完成范围与约束初始化`
    - `run_created -> 已创建本次运行并准备推进`
    - 未知 key -> `已推进到下一阶段（内部记录已保存）`
  - 移除机械化文案（如“为了更像真实员工客服…”），统一负责人三段式。
  - 默认关闭自动 TRACE 进度推送；仅在 `CTCP_TG_PROGRESS_PUSH=1` 时开启。
  - 新增显式触发：
    - 用户消息：`查看进度` / `debug`
    - 命令：`/debug`
  - 清理用户可见回复中的内部术语/路径/文件名泄露。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 增加 `test_reply_payload_sanitizes_internal_tokens_and_keeps_ops`。
  - 同步更新三段式断言与 note 回显行为断言。
- `docs/10_team_mode.md`
  - 增补双通道输出契约与 debug 触发说明。
- `meta/tasks/CURRENT.md`
  - 追加本次 DoD/Acceptance。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py` => exit `0`
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（9 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=10`)
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-103616` (`passed=14 failed=0`)
  - python unit tests: `Ran 82 tests, OK (skipped=3)`

### Questions
- None

### Demo
- 用户侧：默认只看三段式（无 `guardrails_written` / `RUN.json` / `TRACE` / `outbox` 文案）。
- 显式进度：发送“查看进度”或 `debug`（或 `/debug`）查看里程碑摘要。
- 运维侧：`run_dir/logs/telegram_cs_bot.ops.jsonl` 保留内部 key/path 与净化前信息。

