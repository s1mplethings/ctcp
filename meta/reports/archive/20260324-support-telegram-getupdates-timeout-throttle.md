# Demo Report - LAST

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260324-support-telegram-getupdates-timeout-throttle.md`](archive/20260324-support-telegram-getupdates-timeout-throttle.md)
- Date: 2026-03-24
- Topic: Telegram `getUpdates` read timeout 降噪与可恢复轮询稳态化

### Readlist

- `AGENTS.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`

### Plan

1. 将 `run_telegram_mode` 的 read timeout 识别为可恢复 timeout 分支，避免 `streak=1/2/3` 高频 error 日志。
2. 在 timeout 分支保持 backoff 与 `run_proactive_support_cycle` 调用，不影响后台推进。
3. 新增 runtime wiring 回归，验证日志降噪与 proactive 调用连续性。
4. 跑 focused tests + canonical verify，补齐任务/报告闭环。

### Changes

- `scripts/ctcp_support_bot.py`
  - 新增 `_is_telegram_read_timeout(exc, error_text)`，集中识别 read timeout 类异常。
  - 新增 `_should_log_timeout_streak(streak)`，将 timeout 日志降为稀疏阈值输出（5/10/20n）。
  - `run_telegram_mode()` 中 timeout-like 分支改为 timeout 降噪路径；非 timeout 异常保持原有 error 日志策略。
  - timeout 分支继续执行 backoff 与 `run_proactive_support_cycle()`，保证 idle/proactive 行为不退化。
- `tests/test_runtime_wiring_contract.py`
  - 新增 `test_run_telegram_mode_read_timeout_logs_are_throttled`：
    - 模拟连续 5 次 `TimeoutError("The read operation timed out")`。
    - 断言不再出现 `telegram getUpdates error (streak=1/2/3)` 噪声。
    - 断言出现 `telegram getUpdates timeout (streak=5)` 稀疏日志。
    - 断言 timeout 期间 proactive cycle 仍被调用。
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260324-support-telegram-getupdates-timeout-throttle.md`

### Verify

- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (22 tests)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (51 tests)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests; from canonical verify)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests; from canonical verify)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point observed during this task:
  - 首次 canonical verify 因执行超时（timeout 184s）中断，不是门禁失败。
- minimal fix strategy applied:
  - 仅延长命令超时时间后重跑，所有 gates 通过。

### Questions

- None.

### Demo

- Telegram 长轮询偶发 read timeout 时，不再出现连续 `streak=1/2/3` error 刷屏。
- timeout 仍会按阈值输出可观测日志（例如 `streak=5`），并保持后台 proactive cycle 正常推进。
- 非 timeout 异常仍保留 error 级别处理，不影响真正故障定位。

### Integration Proof

- upstream: `TelegramClient.get_updates` long polling
- current_module: `scripts/ctcp_support_bot.py::run_telegram_mode`
- downstream: stderr 可观测性噪声控制 + proactive idle push 连续性
- source_of_truth: timeout classifier + streak threshold policy
- final lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260324-214334` (`passed=14`, `failed=0`)
