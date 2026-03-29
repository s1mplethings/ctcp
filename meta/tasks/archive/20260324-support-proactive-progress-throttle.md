# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-proactive-progress-throttle.md`](archive/20260324-support-proactive-progress-throttle.md)
- Date: 2026-03-24
- Topic: Support 主动进度推送节流（仅用户询问或低频保活）
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-proactive-progress-throttle`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 线上 Telegram 记录出现“用户问进度后，紧跟一条重复进度推送”，用户明确要求禁止“每次回答后跟着一个进度”。
- Dependency check: `ADHOC-20260324-support-runtime-progress-guard-hardening` = `done`。
- Scope boundary: 仅调整 support proactive/controller 推送节奏与文案边界，不改 bridge/orchestrator 主流程。

## Task Truth Source (single source for current task)

- task_purpose: 将主动进度通知改为“仅用户问进度或低频保活触发”，并保持普通客户可见进度语气。
- allowed_behavior_change:
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-proactive-progress-throttle.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-proactive-progress-throttle.md`
- forbidden_goal_shift: 不扩展到无关模块，不改 frontend bridge 契约，不引入新的并行事实源。
- in_scope_modules:
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-proactive-progress-throttle.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-proactive-progress-throttle.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `docs/00_CORE.md`
  - `src/`
  - `include/`
- completion_evidence: 不再出现“回复后紧跟重复进度推送”；主动进度只在 keepalive 周期发送，用户问进度仍可即时收到状态回复。

## Analysis / Find (before plan)

- Entrypoint analysis: 重复推送发生在 `SUPPORT_REPLY_WRITTEN` 后短时间 `SUPPORT_PROGRESS_PUSHED`，触发点在 `run_proactive_support_cycle` + controller `status_changed` 分支。
- Downstream consumer analysis: Telegram 对外消息直接受 `_emit_controller_outbound_jobs` 影响。
- Source of truth: `ctcp_support_controller.decide_and_queue` 的 job 触发条件与 `remember_progress_notification` 状态。
- Current break point / missing wiring: `status_changed` 会在用户刚收到回复后再次触发 progress job，造成体验重复。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: process_message 回复写入 + controller notification state。
- current_module: proactive decide/queue + outbound emit。
- downstream: Telegram 用户可见主动进度通知节奏。
- source_of_truth: notification_state(last_progress_hash/ts) + keepalive interval。
- fallback: first failure + minimal fix。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许只改测试不改 runtime。
  - 不允许跳过 canonical verify。
  - 不允许用内部 gate 语义替代普通客户可见进度语气。
- user_visible_effect: 不再“每次回复后追加重复进度”；主动通知改为低频保活，文案保持普通进度表达。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: proactive progress channel no longer emits immediate follow-on progress right after user-facing replies; progress pushes are limited to keepalive interval while user-query replies remain in process_message path
- [x] DoD-2: proactive progress text remains ordinary customer-facing progress wording and avoids internal gate/owner leakage patterns
- [x] DoD-3: focused regressions and canonical verify confirm no duplicate follow-on progress while keepalive progress still works

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (runtime/event chain scan)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 在 controller 中关闭 `status_changed` 即时主动推送，仅保留 keepalive 到期推送（用户问进度仍走 process_message）。
2) 确保主动推送文案保持普通进度描述，不暴露内部 gate owner/技术细节。
3) 更新并补充回归（重复推送抑制 + keepalive 仍可触发）。
4) 跑 focused tests + canonical verify。
5) 更新报告与归档，关闭 queue item。

## Check / Contrast / Fix Loop Evidence

- check-1: 事件链显示 `SUPPORT_REPLY_WRITTEN` 后 12 秒出现 `SUPPORT_PROGRESS_PUSHED(reason=status_changed)`。
- contrast-1: 用户要求禁止“每次回答后跟着一个进度”。
- fix-1: 主动进度改为 keepalive-only，不再因内部状态变化立即推送。
- check-2: 状态通知应是普通进度，不是内部门禁术语。
- contrast-2: 用户可见通知应保持通俗进度表达。
- fix-2: 统一通过 grounded status 文案路径输出，避免内部 gate owner 暴露。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: reply path 与 proactive path 的通知节奏约束统一。
  - accumulated: notification_state 持续积累 keepalive 与已发状态哈希。
  - consumed: runtime wiring/humanization 回归直接验证“无紧跟重复推送 + keepalive 可用”。

## Notes / Decisions

- Default choices made: 优先按用户要求关闭 status_changed 即时推送，保留低频 keepalive 与用户主动查询响应。
- Alternatives considered: 保留 status_changed 但加更短去重窗口；不采纳（仍可能触发“回复后紧跟一条”）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 属于体验节奏修复，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded runtime/controller behavior patch.
- persona_lab_impact: none（本轮聚焦 proactive cadence，不改 persona rubric）。

## Results

- Files changed:
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-proactive-progress-throttle.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-proactive-progress-throttle.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (49 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | Support 主动进度推送节流（仅用户询问或低频保活） | [→](archive/20260324-support-proactive-progress-throttle.md) |
| 2026-03-24 | Support 运行时 task-progress 预发送硬校验加固 | [→](archive/20260324-support-runtime-progress-guard-hardening.md) |
| 2026-03-24 | 客服/前台推进型对话硬约束合同化与可执行 lint | [→](archive/20260324-support-hard-dialogue-progression-contract.md) |
| 2026-03-24 | 客服进度真值修复与状态回复去机械化 | [→](archive/20260324-support-progress-truth-and-humanized-status.md) |
| 2026-03-24 | 客服主动通知控制器重构与状态推进拆分 | [→](archive/20260324-support-proactive-controller-refactor.md) |
| 2026-03-24 | librarian 后续角色统一 API 路由 | [→](archive/20260324-post-librarian-api-routing.md) |
| 2026-03-24 | 修复 triplet runtime wiring 基线失败链 | [→](archive/20260324-triplet-runtime-wiring-baseline-repair.md) |
| 2026-03-24 | API 连通性与项目内接线可用性验证 | [→](archive/20260324-api-connectivity-project-wiring-check.md) |
| 2026-03-24 | Support 发包动作只允许“测试通过 + 最终阶段”触发 | [→](archive/20260324-support-package-final-stage-gate.md) |
| 2026-03-24 | Support 单主流程状态机（禁用 Telegram 快速脚手架旁路） | [→](archive/20260324-support-single-mainline-state-machine.md) |

Full archive: `meta/tasks/archive/`
