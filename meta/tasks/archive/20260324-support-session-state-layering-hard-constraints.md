# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-session-state-layering-hard-constraints.md`](archive/20260324-support-session-state-layering-hard-constraints.md)
- Date: 2026-03-24
- Topic: Support 会话单主线状态、历史分层与阶段推进硬约束落地
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-session-state-layering-hard-constraints`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户明确要求客服/frontdesk/support bot 严格拆分前后台职责，强制单主任务线、分层历史、阶段推进和反中断失焦。
- Dependency check: `ADHOC-20260324-support-proactive-progress-throttle` = `done`。
- Scope boundary: 只做 support/frontdesk runtime 状态与记忆结构改造及回归测试，不改 bridge/orchestrator 主流程契约。

## Task Truth Source (single source for current task)

- task_purpose: 将“会话、状态、历史与推进硬约束”从规则描述落为可执行 runtime 状态结构、回复上下文约束与测试证据。
- allowed_behavior_change:
  - `docs/10_team_mode.md`
  - `frontend/frontdesk_state_machine.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_frontdesk_state_machine.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-session-state-layering-hard-constraints.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-session-state-layering-hard-constraints.md`
- forbidden_goal_shift: 不扩展到无关 provider/dispatcher/refactor，不改 UI 风格资产，不引入并行真值源。
- in_scope_modules:
  - `docs/10_team_mode.md`
  - `frontend/frontdesk_state_machine.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_frontdesk_state_machine.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-session-state-layering-hard-constraints.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-session-state-layering-hard-constraints.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_dispatch.py`
  - `docs/00_CORE.md`
  - `src/`
  - `include/`
- completion_evidence: session state 落地单主任务字段 + 历史分层 + message intent 分类 + stage 映射，并经 focused tests 与 canonical verify 验证。

## Analysis / Find (before plan)

- Entrypoint analysis: support 对话入口在 `scripts/ctcp_support_bot.py::process_message`，前台状态判定在 `frontend/frontdesk_state_machine.py`。
- Downstream consumer analysis: `build_support_prompt()`、`build_final_reply_doc()`、Telegram proactive controller 发送路径消费这些状态。
- Source of truth: support session state (`artifacts/support_session_state.json`) + bridge run truth + controller decision path。
- Current break point / missing wiring:
  - 现有状态缺少强制 `active_goal/stage/blocker/next_action` 真值槽位。
  - 历史虽有 memory zone，但缺少显式四层结构与压缩字段。
  - 没有将 `continue|clarify|constraint_update|new_task|small_talk|status_check` 持久化为每轮 intent 结果。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram/stdin support ingress -> `process_message`。
- current_module: frontdesk state derivation + support session state normalization + prompt context assembly。
- downstream: provider prompt 输入边界、customer-facing reply 以及 proactive controller 推送节奏。
- source_of_truth: bound run status/gate + support session `active_*` fields + layered memory。
- fallback: first failure + minimal fix recorded in report。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许只改文档不改 runtime。
  - 不允许只改测试不改状态结构。
  - 不允许跳过 canonical verify。
- user_visible_effect: 回复更连续地围绕单主任务推进；插话不再冲掉主线；长对话不再依赖完整 raw 历史。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: support session state persists one active task truth (`active_task_id/active_run_id/active_goal/active_stage/active_blocker/active_next_action`) and non-new-task turns do not silently overwrite it
- [x] DoD-2: history context is layered into `raw_turns`, `working_memory`, `task_summary`, and `user_preferences`; frontdesk prompt path consumes working/task summary plus bounded recent raw turns instead of full raw chat
- [x] DoD-3: message intent classification (`continue|clarify|constraint_update|new_task|small_talk|status_check`) and stage mapping (`INTAKE/CLARIFY/PLAN/EXECUTE/VERIFY/WAIT_USER_DECISION/FINALIZE/DELIVER/RECOVER`) are persisted and covered by focused regressions plus canonical verify evidence

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (runtime/state/tests scan complete)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 在 `support_session_state` 增加 `active_*` 真值与 `history_layers` 四层结构，并在 normalize/save 周期中维护。
2) 在 frontdesk/support runtime 增加 message intent 分类、stage 映射与 `new_task` 才切主线规则。
3) 调整 prompt 组装逻辑，优先消费 `working_memory + task_summary + recent raw_turns`。
4) 扩展 focused 回归覆盖单主线、插话不中断主线、历史分层和 stage/intent 持久化。
5) 跑 focused tests + canonical verify。
6) 更新 `meta/reports/LAST.md` 与归档，关闭任务。

## Check / Contrast / Fix Loop Evidence

- check-1: 当前 session state 主要是 `project_memory/turn_memory/frontdesk_state`，未显式强制 `active_*` 六元组。
- contrast-1: 用户要求任意时刻单主任务且必须有 `active_task_id/run_id/goal/stage/blocker/next_action`。
- fix-1: 增加并持久化 `active_*` 结构，所有回复前先绑定该结构。
- check-2: prompt 虽限制 history 条数，但缺少显式四层 memory contract。
- contrast-2: 用户要求 raw/working/summary/preferences 分层并可压缩。
- fix-2: 引入 `history_layers` 并在每轮更新/压缩，prompt 只取 working/summary + 少量 raw。
- check-3: 缺少每轮 message intent 的可审计分类字段。
- contrast-3: 用户要求插话先分类再动作，避免主线丢失。
- fix-3: 增加 `message_intent_classification` 与 routing decisions 持久化字段并测通。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: session state -> prompt context -> final reply/proactive path 全链路连接。
  - accumulated: history_layers/task_summary 会随轮次累积并压缩。
  - consumed: tests 和 runtime 回复路径消费 `active_*`、intent、stage 与层化历史。

## Notes / Decisions

- Default choices made: 复用现有 frontdesk/controller 架构，增量加固状态字段，不做架构重写。
- Alternatives considered: 全量重构 support FSM；不采纳（超出本轮最小闭环）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 本轮是硬约束落地，不是新线上故障复盘；暂不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a scoped runtime hardening patch for the current support lane state schema.
- persona_lab_impact: none（不改 persona 资产，仅改 runtime state/wiring/tests）。

## Results

- Files changed:
  - `docs/10_team_mode.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-session-state-layering-hard-constraints.md`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-session-state-layering-hard-constraints.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> `0` (6 tests)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (51 tests)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests; from canonical verify run)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests; from canonical verify run)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | Support 会话单主线状态、历史分层与阶段推进硬约束落地 | [→](archive/20260324-support-session-state-layering-hard-constraints.md) |
| 2026-03-24 | Support 主动进度推送节流（仅用户询问或低频保活） | [→](archive/20260324-support-proactive-progress-throttle.md) |
| 2026-03-24 | Support 运行时 task-progress 预发送硬校验加固 | [→](archive/20260324-support-runtime-progress-guard-hardening.md) |
| 2026-03-24 | 客服/前台推进型对话硬约束合同化与可执行 lint | [→](archive/20260324-support-hard-dialogue-progression-contract.md) |
| 2026-03-24 | 客服进度真值修复与状态回复去机械化 | [→](archive/20260324-support-progress-truth-and-humanized-status.md) |
| 2026-03-24 | 客服主动通知控制器重构与状态推进拆分 | [→](archive/20260324-support-proactive-controller-refactor.md) |
| 2026-03-24 | librarian 后续角色统一 API 路由 | [→](archive/20260324-post-librarian-api-routing.md) |
| 2026-03-24 | 修复 triplet runtime wiring 基线失败链 | [→](archive/20260324-triplet-runtime-wiring-baseline-repair.md) |
| 2026-03-24 | API 连通性与项目内接线可用性验证 | [→](archive/20260324-api-connectivity-project-wiring-check.md) |
| 2026-03-24 | Support 发包动作只允许“测试通过 + 最终阶段”触发 | [→](archive/20260324-support-package-final-stage-gate.md) |

Full archive: `meta/tasks/archive/`
