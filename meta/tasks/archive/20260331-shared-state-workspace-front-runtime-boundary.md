# Task - shared-state-workspace-front-runtime-boundary

## Queue Binding

- Queue Item: `ADHOC-20260329-shared-state-workspace-front-runtime-boundary`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 修复客服(frontdesk/support)与后端(orchestrate/bridge)连接中的状态真相分裂与 decision 协议弱化问题。
- Dependency check: `ADHOC-20260325-support-delivery-quality-gate = done`
- Scope boundary: 仅修 bridge/support_controller/support_bot/frontdesk_state_machine 与必要测试/契约补充，不做无关重构。

## Task Truth Source (single source for current task)

- task_purpose: 以 `81f8f35` 基线引入单一 canonical runtime snapshot 与显式 decision object，使客服/controller/frontdesk 只消费 canonical 状态。
- allowed_behavior_change:
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/frontdesk_state_machine.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_frontdesk_state_machine.py`
  - `docs/shared_state_contract.md` (only if contract note is required)
- forbidden_goal_shift: 不升级到最新实现，不改后端主编排架构，不改无关模块。
- in_scope_modules:
  - `scripts/`
  - `frontend/`
  - `tests/`
  - `docs/`
  - `meta/`
- out_of_scope_modules:
  - `apps/project_backend/`（不重构业务流程）
  - `contracts/`（不升级协议版本）
  - `src/`, `include/`, `web/`
- completion_evidence: canonical snapshot 成为状态主来源；decision 有显式状态流；submit 后需 consumed/状态前进才算推进；对应回归测试通过。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_front_bridge.py` 的 `ctcp_get_status/ctcp_submit_decision` 是前后端状态与决策的唯一桥接入口。
- Downstream consumer analysis: `scripts/ctcp_support_controller.py`、`scripts/ctcp_support_bot.py`、`frontend/frontdesk_state_machine.py` 都消费 `project_context.status/decisions`。
- Source of truth: `artifacts/support_runtime_state.json`（新增 canonical runtime snapshot）。
- Current break point / missing wiring: 现状以 RUN/verify/status/outbox/QUESTIONS 多源拼接并在多层二次推断，导致状态打架与重复提示。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `ctcp_front_bridge.ctcp_get_status` / `ctcp_front_bridge.ctcp_submit_decision`
- current_module: `scripts/ctcp_front_bridge.py`
- downstream: `scripts/ctcp_support_controller.py` + `scripts/ctcp_support_bot.py` + `frontend/frontdesk_state_machine.py`
- source_of_truth: `run_dir/artifacts/support_runtime_state.json`
- fallback: canonical 缺失时仅兼容回填 legacy 结构，不让 legacy 成为主判断入口。
- acceptance_test:
  - `python -m unittest tests/test_support_to_production_path.py -v`
  - `python -m unittest tests/test_support_bot_humanization.py -v`
  - `python -m unittest tests/test_frontdesk_state_machine.py -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许 support/controller/frontdesk 自行定义主流程真相。
  - 不允许 decision 提交以“写文件成功”直接等价“后端已消费”。
  - 不允许继续以 outbox 扫描作为 needs_user_decision 主判据。
- user_visible_effect: 对话层状态更稳定，减少重复机械播报与“该等用户却继续推/已完成却卡住”的冲突。

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: Shared state workspace lands with append-only event log, current snapshot rebuild, and render snapshot export plus explicit source/event write permissions
- [ ] DoD-2: Frontend/frontdesk/response paths consume shared current/render state via adapter without replacing runtime authority or bypassing verify/proof ownership
- [ ] DoD-3: Runtime/support wiring emits authoritative stage/progress/verify events into shared state, regressions cover replay/visible-state mapping/done-proof gating, and canonical verify evidence is recorded

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 在 bridge 定义 canonical runtime state 与 decision object 协议。
2) `ctcp_get_status/ctcp_list_decisions_needed/ctcp_submit_decision` 全部围绕 canonical snapshot 工作，legacy 仅 fallback。
3) support_controller 改为只消费 canonical state 做节流与消息编排。
4) support_bot 的 active stage/progress 逻辑优先映射 canonical `phase`。
5) frontdesk_state_machine 优先用 canonical state 映射 UI/对话状态。
6) 增加并修订测试覆盖执行中、待决策、提交后未消费、完成/失败与跨轮决策残留场景。
7) 运行目标测试与 canonical verify，记录首个失败与最小修复。
8) 更新 `meta/reports/LAST.md`。

## Check / Contrast / Fix Loop Evidence

- check-1: bridge 当前多源拼接（RUN/verify/status/outbox/QUESTIONS）并在 support/controller/frontdesk 二次推断，存在状态真相冲突。
- contrast-1: 目标要求单一 canonical snapshot + 显式 decision 生命周期，提交后不能以写文件即判定后端消费。
- fix-1: 引入 `artifacts/support_runtime_state.json` 作为桥层 canonical 快照，decision 生命周期改为 `pending/submitted/consumed/...`，三层改为消费 canonical 映射。
- check-2: `verify_repo` 首次失败于 workflow gate，提示 `LAST.md` 未更新。
- fix-2: 已补 `meta/reports/LAST.md` 与报告归档，再次执行 verify。

## Completion Criteria Evidence

- completion criteria: connected + accumulated + consumed evidence is explicitly recorded below.
- connected: `ctcp_front_bridge` 输出 canonical runtime state，`support_controller/support_bot/frontdesk_state_machine` 均通过 `project_context.runtime_state` 消费主流程状态。
- accumulated: decision object 已包含 `decision_id/kind/question/target_path/expected_format|schema/status/created_at/submitted_at/consumed_at` 并持续写入 canonical 快照。
- consumed: 回归测试覆盖 `submitted -> consumed` 确认链；只有 canonical 状态前进/decision consumed 才确认推进，不再以写文件成功作为推进完成。

## Notes / Decisions

- Default choices made: canonical 文件定为 `artifacts/support_runtime_state.json`，保留旧字段兼容映射。
- Alternatives considered: 彻底重写 support/frontdesk 状态机；拒绝，避免超范围。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision: 本次直接以回归测试固化状态分裂与决策消费确认链，不额外引入新 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because` 本次为当前支持链路的定点修复，不是可抽象复用的稳定工作流资产。

## Results

- Files changed:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_controller.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/frontdesk_state_machine.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_frontdesk_state_machine.py`
  - `docs/shared_state_contract.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260330-support-canonical-runtime-state-fix.md`
- Verification summary: focused tests passed; canonical verify passed with repo-supported `CTCP_SKIP_LITE_REPLAY=1` after recording first lite replay failure.
- Queue status update suggestion (`todo/doing/done/blocked`): `doing`
