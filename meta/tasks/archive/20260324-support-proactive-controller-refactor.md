# Task - support-proactive-controller-refactor

## Queue Binding

- Queue Item: `ADHOC-20260324-support-proactive-controller-refactor`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户要求修复客服主动通知能力并将状态推进判断从客服 bot 文案层拆分到后台 controller。
- Dependency check: `ADHOC-20260324-support-single-mainline-state-machine` = `blocked` (单主流程边界已落地，本任务在其上补 controller 分层)。
- Scope boundary: 仅改 support proactive/controller 相关链路与必要测试，不改 bridge/orchestrator 语义。

## Task Truth Source (single source for current task)

- task_purpose: 用最小改动引入规则驱动 support controller，完成主动通知、去重、cooldown 与受控结果通知。
- allowed_behavior_change:
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `docs/10_team_mode.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-proactive-controller-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-proactive-controller-refactor.md`
- forbidden_goal_shift: 不引入第二事实源；不在 support 层脑补完成态；不重写主架构。
- in_scope_modules:
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `docs/10_team_mode.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-proactive-controller-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-proactive-controller-refactor.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `frontend/frontdesk_state_machine.py`
  - `src/`
  - `include/`
- completion_evidence: controller state transitions and outbound notify decisions are test-covered and grounded in bridge truth; canonical verify evidence recorded.

## Analysis / Find (before plan)

- Entrypoint analysis: `run_proactive_support_cycle` still does fetch/advance/digest/send in one bot module.
- Downstream consumer analysis: only Telegram emit path consumes proactive updates; no generic outbound queue abstraction exists.
- Source of truth: `ctcp_front_bridge.ctcp_get_support_context` (`status/gate/decisions`) plus support session state snapshots.
- Current break point / missing wiring: dedupe signal is only `last_progress_hash`; missing `last_sent_message_hash/last_sent_kind/decision hash/cooldown`.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram idle polling + bound support sessions.
- current_module: proactive notify decision logic and session state normalization.
- downstream: outbound message emission and runtime wiring regressions.
- source_of_truth: bridge run status + decision list + verify result.
- fallback: if verify fails, record first failure and minimal fix path.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许在 support 层绕开 run truth 发结果
  - 不允许仅文案变更替代控制链路变更
  - 不允许引入并行状态真源
- user_visible_effect: 状态变化时客服可主动通知、不会重复刷屏、用户决策问题不会重复问、结果只在真实 ready 时通知。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: support backend uses a dedicated controller state machine to decide proactive notifications from bridge run truth instead of bot-side ad hoc branching
- [x] DoD-2: proactive notifications are deduplicated with status/message hashes plus cooldown, including one-shot decision prompts and low-frequency execution keepalive
- [x] DoD-3: support regressions cover proactive progress/decision/result/error paths and canonical verify evidence is recorded with first failure plus minimal fix if gate is blocked

## Plan

1) Add standalone `ctcp_support_controller.py`.
2) Extend support session state with `controller_state`, richer `notification_state`, and `outbound_queue`.
3) Integrate controller in proactive cycle while keeping bot as Telegram delivery shell.
4) Add/adjust focused regressions for proactive notify dedupe and state transitions.
5) Run focused tests and canonical verify, then record evidence in reports.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: proactive logic in bot mixed run-state judgment with Telegram emission.
  - contrast-1: target boundary requires controller-owned state and notify-kind decisions.
  - fix-1: extracted controller decisions into `scripts/ctcp_support_controller.py` and left bot as delivery shell.
  - check-2: only `last_progress_hash` dedupe existed and decision prompts could be re-asked.
  - contrast-2: target requires prompt-hash dedupe + cooldown + sent-kind/message hash tracking.
  - fix-2: added `last_seen_status_hash`, `last_sent_message_hash`, `last_sent_kind`, `last_decision_prompt_hash`, `cooldown_until_ts`.
  - check-3: result notification gate was not represented as explicit backend controller state.
  - contrast-3: result notify must be triggered only on true final-ready run truth.
  - fix-3: controller emits `result` jobs only when `verify_result=PASS` and final run status with no pending decision.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: proactive Telegram cycle now consumes controller outbound jobs.
  - accumulated: controller/notification/outbound queue fields persist in support session state.
  - consumed: emitted proactive messages are selected by controller kind (`progress|decision|result|error`) and still grounded on bridge truth.

## Notes / Decisions

- Default choices made: keep bridge as only truth source and use rule-based controller decisions.
- Alternatives considered: keep all proactive logic inside bot; rejected because it preserves coupling.
- Any contract exception reference: none.
- Issue memory decision: continue existing support/runtime issue chain without adding duplicate entries.
- Skill decision: `skillized: no, because this is a repo-local bounded runtime refactor`.
- persona_lab_impact: none.

## Results

- Files changed:
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `docs/10_team_mode.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-proactive-controller-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-proactive-controller-refactor.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_controller.py scripts/ctcp_support_bot.py tests/test_runtime_wiring_contract.py tests/test_support_bot_humanization.py` -> `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (43 tests)
  - `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> `0` (6 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion: done
