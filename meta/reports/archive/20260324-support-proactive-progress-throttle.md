# Demo Report - LAST

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260324-support-proactive-progress-throttle.md`](archive/20260324-support-proactive-progress-throttle.md)
- Date: 2026-03-24
- Topic: Support 主动进度推送节流（仅用户询问或低频保活）

### Readlist

- `AGENTS.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_controller.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664/events.jsonl`

### Plan

1. 将 proactive progress 触发从 `status_changed` 改为 keepalive-only，避免“回复后紧跟一条重复进度”。
2. 保留用户主动询问进度时的即时回复路径（`process_message`），不被主动推送覆盖。
3. 给 proactive 文案增加内部 gate 泄漏兜底，确保对外表达保持普通进度语气。
4. 跑 focused 回归与 canonical verify，并重启 Telegram bot 生效。

### Changes

- `scripts/ctcp_support_controller.py`
  - `decide_and_queue()` 的 progress 触发条件改为仅 `keepalive_due`，移除 `status_changed` 立即主动推送。
- `scripts/ctcp_support_bot.py`
  - 新增 `_normalize_proactive_progress_reply_text()`，对 proactive progress 做内部 gate 词泄漏兜底普通化。
  - `_emit_controller_outbound_jobs()` 在 `kind=progress` 时应用普通化处理。
- `tests/test_runtime_wiring_contract.py`
  - 调整 proactive idle 用例为 keepalive 触发场景。
- `tests/test_support_bot_humanization.py`
  - 调整 progress dedupe 用例适配 keepalive-only。
  - 新增 `test_support_controller_does_not_push_progress_immediately_on_status_changed`。
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-support-proactive-progress-throttle.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260324-support-proactive-progress-throttle.md`

### Verify

- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (49 tests)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests; from canonical verify)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests; from canonical verify)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point observed during this task:
  - none（本轮 focused/canonical 首次执行即通过）
- minimal fix strategy applied:
  - N/A

### Questions

- None.

### Demo

- 用户消息后的即时答复仍保留（用户问进度立即回）。
- 主动进度改为低频 keepalive，不再因为内部状态变动在答复后立刻再推一条。
- 若 proactive 文案出现内部 gate/owner 术语，会自动回落为普通进度表达。

### Integration Proof

- upstream: `process_message` reply path + controller notification state
- current_module: `ctcp_support_controller.decide_and_queue` + `ctcp_support_bot._emit_controller_outbound_jobs`
- downstream: Telegram 对外主动进度通知节奏与文案可见性
- source_of_truth: `notification_state.last_progress_ts/hash` + keepalive interval
- final lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260324-195246` (`passed=14`, `failed=0`)
