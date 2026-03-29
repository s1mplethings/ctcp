# Task - support-progress-truth-and-humanized-status

## Queue Binding

- Queue Item: `ADHOC-20260324-support-progress-truth-and-humanized-status`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户反馈客服回复机械、重复同步且进度描述与真实 run 阻塞状态不一致。
- Dependency check: `ADHOC-20260324-support-proactive-controller-refactor` = `done`。
- Scope boundary: 仅修复 support 进度真值/去重/文案表达与 dispatch 分发契约一致性，不改 orchestrator 主流程语义。

## Task Truth Source (single source for current task)

- task_purpose: 修复客服状态回复中的三类缺口：阻塞真值判定、主动推送去重漂移，并校验 analysis/guardrails 路由契约一致性；同时降低状态文案机械重复感。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_dispatch.py`
  - `frontend/response_composer.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-progress-truth-and-humanized-status.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-progress-truth-and-humanized-status.md`
- forbidden_goal_shift: 不改 run truth 来源；不引入第二状态机；不把修复扩展成架构重写。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_dispatch.py`
  - `frontend/response_composer.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-progress-truth-and-humanized-status.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-progress-truth-and-humanized-status.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `docs/00_CORE.md`
  - `src/`
  - `include/`
- completion_evidence: 同状态不重复推送、阻塞描述与 gate.state 对齐、dispatch 路由契约一致并有回归锁定、状态回复模板具备非机械表达并通过回归。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_support_bot.py::build_progress_binding` 只在 `run_status=blocked` 才给阻塞话术，漏掉 `running + gate.blocked`。
- Downstream consumer analysis: `frontend/response_composer.py::_compose_progress_update_reply` 使用固定三段式，容易形成机械重复。
- Source of truth: `ctcp_front_bridge.ctcp_get_support_context` 的 `status.run_status + gate.state/reason/path + decisions`。
- Current break point / missing wiring:
  - controller 与 support 侧使用不同 hash 域，`last_progress_hash` 被覆盖后导致去重失效。
  - `scripts/ctcp_dispatch.py::derive_request` 将 `analysis.md` 错配为 `action=plan_draft`。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: support Telegram proactive cycle + status query rendering path。
- current_module: support progress binding / dispatch derive_request / frontend progress composer。
- downstream: proactive push dedupe，用户状态回复，dispatch outbox action 选择。
- source_of_truth: bound run status + gate + decisions from bridge。
- fallback: 记录 first failure point 并给最小修复。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许只改 prompt 文案掩盖状态真值问题。
  - 不允许忽略 `gate.state=blocked` 的真实卡点。
  - 不允许继续保留 analysis/plan 错配映射。
- user_visible_effect: 客服状态回复更像真实进展播报，不会同状态重复轰炸，且“无阻塞”误报消失。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: progress binding truthfully reflects gate-blocked internal waits even when run_status remains running
- [x] DoD-2: proactive dedupe remains stable across controller/support state writes and same-state updates do not re-push
- [x] DoD-3: dispatch mapping + frontend status phrasing are coherent and tested

## Plan

1) 修正 `build_progress_binding` 的 blocked 判定。
2) 修正 `derive_request` 中 `analysis.md` action/target。
3) 修正 proactive dedupe hash 漂移（controller hash 与 support 侧记忆一致）。
4) 微调 `response_composer` 状态文案模板，减少机械重复。
5) 增补/更新回归测试并执行 focused + canonical verify。

## Check / Contrast / Fix Loop Evidence

- check-1: `run_status=running + gate.state=blocked` 被描述为“暂无阻塞”。
- contrast-1: gate truth 应优先反映真实阻塞阶段。
- fix-1: 以 gate-blocked（且无用户决策）触发阻塞话术。
- check-2: controller 发完消息后被 support digest 覆写，导致下一轮又判定 changed。
- contrast-2: dedupe hash 应保持单域一致。
- fix-2: 保存通知记忆时优先沿用 controller 的 `status_hash`。
- check-3: dispatch `analysis/guardrails` 属于 `plan_draft` family 行为，需确认契约与 simlab 场景保持一致。
- contrast-3: 路由行为应与 `S17/S19` 场景和 B026 行为契约一致，避免 outbox 断言回归。
- fix-3: 保持 `plan_draft` family 映射并补充 provider 侧回归测试锁定预期。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: proactive controller 判定与 support 状态写回一致。
  - accumulated: dedupe 字段持续保留并在重复轮询中被消费。
  - consumed: 用户可见状态回复按真实阶段/阻塞变化更新。

## Notes / Decisions

- Default choices made: 保持最小补丁，不改 bridge contract。
- Alternatives considered: 直接禁用 proactive 推送；不采纳（会丢失主动同步能力）。
- Any contract exception reference: none.
- Issue memory decision: 沿用当前 support/runtime 问题链，避免重复新链。
- Skill decision: `skillized: no, because this is a bounded repo-local repair`.
- persona_lab_impact: none.

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `frontend/response_composer.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_provider_selection.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-progress-truth-and-humanized-status.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-progress-truth-and-humanized-status.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (45 tests)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0` (30 tests)
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` -> `0` (10 tests)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion: done
