# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-telegram-getupdates-timeout-throttle.md`](archive/20260324-support-telegram-getupdates-timeout-throttle.md)
- Date: 2026-03-24
- Topic: Telegram `getUpdates` read timeout 降噪与可恢复轮询稳态化
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-telegram-getupdates-timeout-throttle`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 线上 support bot 日志连续出现 `telegram getUpdates error (streak=1/2/3): The read operation timed out`，属于可恢复超时却形成噪声告警。
- Dependency check: `ADHOC-20260324-support-session-state-layering-hard-constraints` = `done`。
- Scope boundary: 仅修复 Telegram long-poll timeout 的日志/轮询处理与回归测试，不改 bridge/orchestrator 主契约。

## Task Truth Source (single source for current task)

- task_purpose: 将 `getUpdates` 读超时从“高频 error 日志”改为“低频 timeout 日志”，并保持超时期间 proactive cycle 继续运行。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
- forbidden_goal_shift: 不扩展到 provider/router 重构，不改前台文案策略，不引入新的状态真值源。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `docs/00_CORE.md`
  - `src/`
  - `include/`
- completion_evidence: timeout streak 日志不再在 `1/2/3` 连续刷屏；timeout 分支仍保留 proactive cycle；focused tests + canonical verify 通过。

## Analysis / Find (before plan)

- Entrypoint analysis: 问题出在 `scripts/ctcp_support_bot.py::run_telegram_mode` 的 `tg.get_updates(offset)` 异常分支。
- Downstream consumer analysis: stderr 日志链路被外部运维观测直接消费，重复 timeout error 会误导为真实故障。
- Source of truth: `run_telegram_mode` getUpdates 异常分类和 backoff 处理逻辑。
- Current break point / missing wiring: read timeout 作为可恢复长轮询常态却被按 error 级别和低 streak 高频打印。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram `getUpdates` long poll。
- current_module: `run_telegram_mode` timeout/error handling。
- downstream: 运维告警噪声、proactive idle cycle 可用性。
- source_of_truth: `get_updates_error_streak` + timeout classifier。
- fallback: first failure + minimal fix recorded in report。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许只改日志文案而不补回归。
  - 不允许吞掉 timeout 后停止 proactive cycle。
  - 不允许跳过 canonical verify。
- user_visible_effect: 机器人行为不变，但 timeout 日志从高频 error 改为稀疏 timeout 提示，噪声显著下降。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Telegram `getUpdates` read timeout 被识别为 timeout-like 可恢复事件，日志从高频 error 降为稀疏 timeout 记录
- [x] DoD-2: timeout 分支仍会执行 backoff 与 `run_proactive_support_cycle`，不因降噪而中断后台推进
- [x] DoD-3: 新增回归覆盖 timeout 降噪与 proactive 连续性，focused tests + canonical verify 通过

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (runtime path + tests scan complete)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 在 `run_telegram_mode` 增加 timeout 分类与稀疏日志阈值。
2) 确保 timeout 分支保持 backoff + proactive cycle。
3) 新增 `test_run_telegram_mode_read_timeout_logs_are_throttled` 回归。
4) 跑 focused tests + canonical verify。
5) 更新 queue/task/report 归档并闭环。

## Check / Contrast / Fix Loop Evidence

- check-1: 线上日志以 `telegram getUpdates error (streak=1/2/3): The read operation timed out` 高频出现。
- contrast-1: read timeout 属于长轮询常见可恢复状态，不应当作为高频 error 噪声输出。
- fix-1: 新增 `_is_telegram_read_timeout` + `_should_log_timeout_streak`，timeout 分支改为稀疏日志策略。
- check-2: 降噪不能影响 idle 时自动推进。
- contrast-2: timeout 分支必须仍执行 `run_proactive_support_cycle`。
- fix-2: 在 timeout 分支继续执行 proactive cycle，新增回归断言 `proactive_spy.call_count == 5`。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: getUpdates timeout 分类直接连接 run loop 日志与 backoff/proactive 行为。
  - accumulated: streak 按阈值稀疏输出（5/10/20n）。
  - consumed: runtime wiring 回归直接消费 timeout 分支并验证日志和 proactive 调用。

## Notes / Decisions

- Default choices made: 把超时当可恢复 timeout 处理，保留非 timeout 异常原有 error 日志策略。
- Alternatives considered: 完全静默 timeout 日志；不采纳（会丢失长期异常可观测性）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 该问题为运行时可恢复噪声，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded runtime + regression patch.
- persona_lab_impact: none（不改 persona 资产）。

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-telegram-getupdates-timeout-throttle.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (22 tests)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (51 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | Telegram `getUpdates` read timeout 降噪与可恢复轮询稳态化 | [→](archive/20260324-support-telegram-getupdates-timeout-throttle.md) |
| 2026-03-24 | Support 会话单主线状态、历史分层与阶段推进硬约束落地 | [→](archive/20260324-support-session-state-layering-hard-constraints.md) |
| 2026-03-24 | Support 主动进度推送节流（仅用户询问或低频保活） | [→](archive/20260324-support-proactive-progress-throttle.md) |
| 2026-03-24 | Support 运行时 task-progress 预发送硬校验加固 | [→](archive/20260324-support-runtime-progress-guard-hardening.md) |
| 2026-03-24 | 客服/前台推进型对话硬约束合同化与可执行 lint | [→](archive/20260324-support-hard-dialogue-progression-contract.md) |
| 2026-03-24 | 客服进度真值修复与状态回复去机械化 | [→](archive/20260324-support-progress-truth-and-humanized-status.md) |
| 2026-03-24 | 客服主动通知控制器重构与状态推进拆分 | [→](archive/20260324-support-proactive-controller-refactor.md) |
| 2026-03-24 | librarian 后续角色统一 API 路由 | [→](archive/20260324-post-librarian-api-routing.md) |
| 2026-03-24 | 修复 triplet runtime wiring 基线失败链 | [→](archive/20260324-triplet-runtime-wiring-baseline-repair.md) |
| 2026-03-24 | API 连通性与项目内接线可用性验证 | [→](archive/20260324-api-connectivity-project-wiring-check.md) |

Full archive: `meta/tasks/archive/`
