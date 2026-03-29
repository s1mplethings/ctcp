# Task - shared-state-workspace-front-runtime-boundary

## Queue Binding

- Queue Item: `ADHOC-20260329-shared-state-workspace-front-runtime-boundary`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 现有 frontend/frontdesk/bridge/runtime/support 状态事实分散，前端需要直接理解后端细节，缺少统一共享状态中枢。
- Dependency check: `ADHOC-20260325-support-delivery-quality-gate = done`
- Scope boundary: 以最小破坏方式新增 shared state 工作区与 adapter 接线，不重写聊天系统，不做大范围重命名。

## Task Truth Source (single source for current task)

- task_purpose: 在 contract-first/verify-gated 架构下引入 stateful shared workspace，统一跨层通信并锁定 authoritative runtime truth 与 visible render truth 边界。
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260329-shared-state-workspace-front-runtime-boundary.md`
  - `meta/reports/archive/20260329-shared-state-workspace-front-runtime-boundary.md`
  - `shared_state/schemas/*.json`
  - `bridge/*.py`
  - `frontend/response_composer.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_shared_state_workspace.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `tests/test_runtime_wiring_contract.py`
  - `docs/shared_state_contract.md`
  - `docs/frontend_runtime_boundary.md`
  - `docs/01_north_star.md`
- forbidden_goal_shift: 不改变仓库 north star；不把完成判定下放给 frontend/support；不移除 runtime/orchestrator/verifier 的权威来源。
- in_scope_modules:
  - `shared_state/`
  - `bridge/`
  - `frontend/`
  - `scripts/`
  - `tests/`
  - `docs/`
  - `meta/`
- out_of_scope_modules:
  - `apps/project_backend/`（不重构服务编排）
  - `contracts/`（不改协议版本）
  - `src/`, `include/`, `web/`（无关 C++/GUI 路径）
- completion_evidence: 事件写入->快照重建->渲染快照导出->前端回复消费链可运行；DONE 仅在 verify+proof 条件满足时出现；event replay 可重建 current.json；canonical verify 证据写入报告。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_support_bot.py::process_message` 是 support/frontend 真实入口，当前在本地拼装 `backend_state/progress_binding/frontdesk_state`。
- Downstream consumer analysis: `frontend/response_composer.py::render_frontend_output` 消费状态并产出用户可见回复；`build_final_reply_doc` 进一步决定回复与动作。
- Source of truth: runtime truth 仍是 run status/verify evidence；shared state 只做跨层通信中枢，不替代 runtime authority。
- Current break point / missing wiring: 没有 append-only shared event log 与统一 current/render snapshot；多个模块直接读内部状态字段并自行裁定 visible/done 语义。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `process_message` / `sync_active_task_truth` / runtime status pull
- current_module: `bridge/state_store.py` + `bridge/snapshot_builder.py` + `bridge/render_adapter.py`
- downstream: `frontend/response_composer.py` and support render/action shaping
- source_of_truth: shared_state `events.jsonl -> current.json -> render.json` with runtime verify/proof constraints
- fallback: shared state 不可用时保留现有 frontend 渲染链路，避免入口中断
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_shared_state_workspace.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许 UI/support shell 直接改 authoritative_stage/verify_result/done flags
  - 不允许 response 层直接成为 runtime truth authority
  - 不允许跳过 append-only event path 直接随意覆盖 current 快照
- user_visible_effect: 用户看到的状态解释继续自然且 grounded，但完成/交付声明只能在 verify+proof 真值成立时出现。

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: Shared state workspace lands with append-only event log, current snapshot rebuild, and render snapshot export plus explicit source/event write permissions
- [ ] DoD-2: Frontend/frontdesk/response paths consume shared current/render state via adapter without replacing runtime authority or bypassing verify/proof ownership
- [ ] DoD-3: Runtime/support wiring emits authoritative stage/progress/verify events into shared state, regressions cover replay/visible-state mapping/done-proof gating, and canonical verify evidence is recorded

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed
- [ ] Patch applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 新增 `shared_state` schema + `bridge` state store/event append/snapshot builder/render adapter。
2) 先在文档里定义 authoritative state vs visible state、写权限、禁止事项，再接代码。
3) 将 frontend `response_composer` 通过 adapter 优先消费 shared current/render，而非散装字段。
4) 将 support/runtime 关键输出通过事件写入 shared state，重建 current/render 并给回复层消费。
5) 增加共享状态专项测试，覆盖事件写入、快照重建、visible collapse、DONE-proof gating、replay。
6) 更新/补充 frontend/runtime 边界测试，确保 UI/support shell 不能凭空宣告完成。
7) `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
8) `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
9) `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
10) Canonical verify gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
11) Completion criteria: prove `connected + accumulated + consumed`.

## Check / Contrast / Fix Loop Evidence

- check-1: frontend/support 当前主要靠临时拼装 `raw_backend_state + progress_binding + frontdesk_state`，缺少跨层唯一共享真值盘。
- contrast-1: 目标要求 authoritative runtime state 与 visible render state 分层，并由 append-only event 驱动快照重建。
- fix-1: 引入 shared event -> current -> render 三段式中枢；用 adapter 维持兼容输入输出，最小范围接线现有 frontend/support。

## Notes / Decisions

- Default choices made: shared state 采用 append-only jsonl + deterministic snapshot rebuild；默认 workspace 在 repo `shared_state/tasks/`，测试用临时目录隔离。
- Alternatives considered: 直接重构全部 frontend/support 模块；拒绝该方案以避免破坏性迁移。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision: 记录“用户可见完成态误判风险”到实现与测试中，本次无需新增问题记忆条目（已有相邻条目覆盖同类风险）。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because` 本次为仓库当前 support/frontend runtime 局部架构收口，不是稳定可复用的独立 workflow 资产。

## Results

- Files changed:
  - `pending`
- Verification summary: `pending`
- Queue status update suggestion (`todo/doing/done/blocked`): `doing`
