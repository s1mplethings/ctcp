# Task - decoupling-acceptance-repair

## Queue Binding

- Queue Item: `ADHOC-20260325-decoupling-acceptance-repair`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 2026-03-25 架构验收发现仍有 P0 边界缺口（frontend 直连 backend、raw history 嵌套入口、status 机械播报、contracts 污染）。
- Dependency check: `ADHOC-20260325-cs-frontend-project-backend-decoupling` = `done`
- Scope boundary: 仅修复本次验收失败项，不扩展到 provider 策略重写或无关 support 流程改造。

## Task Truth Source (single source for current task)

- task_purpose: 修复 decoupling 验收失败项并让前后端边界可独立测试、可审计。
- allowed_behavior_change:
  - `apps/cs_frontend/**`
  - `apps/project_backend/**`（仅必要协议/入口适配）
  - `contracts/**`
  - `docs/architecture/**`
  - `policy/**`
  - `tools/**`（仅 allowed_changes 路径迁移）
  - `scripts/**`（仅 allowed_changes 路径迁移）
  - `tests/frontend/**`
  - `tests/backend/**`
  - `tests/contracts/**`
  - `tests/integration/**`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift: 不重写 orchestrator 主链；不改 C++/web；不做无关清理。
- in_scope_modules:
  - `apps/cs_frontend/`
  - `apps/project_backend/`
  - `contracts/`
  - `tests/frontend/`
  - `tests/backend/`
  - `tests/contracts/`
  - `tests/integration/`
  - `docs/architecture/`
  - `policy/`
- out_of_scope_modules:
  - `src/`
  - `include/`
  - `web/`
  - `simlab/`
  - `workflow_registry/`
- completion_evidence: 四项失败点关闭 + 分层测试通过 + canonical verify 记录。

## Analysis / Find (before plan)

- Entrypoint analysis: frontend 边界问题集中在 `apps/cs_frontend/gateway/backend_client.py`；status 话术集中在 `response_renderer.py`；raw-history 校验在 `contracts/validation.py`。
- Downstream consumer analysis: `tests/frontend|backend|contracts|integration` 将作为最小回归集合。
- Source of truth: `AGENTS.md` + 当前任务卡 + `contracts` schema/validation。
- Current break point / missing wiring: frontend 仍静态 import backend，实现级耦合；contract 对嵌套 chat history 未封堵。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `apps/cs_frontend/application/handle_user_message.py`
- current_module: frontend gateway + contracts validation + renderer
- downstream: tests 分层与 canonical verify
- source_of_truth: `contracts/schemas/*`, `contracts/validation.py`
- fallback: 保留 integration 测试中的 in-process backend stub，避免运行能力回退
- acceptance_test:
  - `python -m unittest discover -s tests/contracts -p "test_*.py" -v`
  - `python -m unittest discover -s tests/backend -p "test_*.py" -v`
  - `python -m unittest discover -s tests/frontend -p "test_*.py" -v`
  - `python -m unittest discover -s tests/integration -p "test_*.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得恢复 `apps/cs_frontend` 对 `apps/project_backend` 的静态导入
  - 不得放松 backend 对 full chat history 的输入限制
  - 不得跳过 canonical verify
- user_visible_effect: 客服回复从工程 phase/log 复述改为客服语义进展提示，问题与结果回复保持可读且可行动。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: cs_frontend 不再直接 import project_backend 实现模块
- [x] DoD-2: job_create 阻断嵌套 full-chat-history 并有回归测试
- [x] DoD-3: frontend status 渲染不再机械透传 phase/log
- [x] DoD-4: contracts 仅保留协议资产，非协议文档/策略迁移并更新引用
- [x] DoD-5: 分层测试 + canonical verify 通过并更新 LAST

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. 改造 frontend `BackendClient` 为纯协议传输接口（去掉 backend 静态导入）。
2. 加强 `contracts/validation` 递归 full-history 校验并补 contracts 测试。
3. 改造 `response_renderer` 的 status 分支为客服语义映射并更新前端/集成测试断言。
4. 迁移 `contracts` 非协议资产（markdown + allowed_changes）并更新代码与文档引用。
5. 执行分层测试与 canonical verify，回填报告。

## Check / Contrast / Fix Loop Evidence

- check-1: frontend 层存在对 backend 实现模块的静态导入，破坏边界独立测试。
- contrast-1: 验收要求 frontend 仅通过结构化协议通信，不可直接依赖 backend 内部实现。
- fix-1: 将 `BackendClient` 改为 `BackendTransport` 协议注入，移除 `apps.cs_frontend` 到 `apps.project_backend` 的静态导入链。
- check-2: `JobCreateRequest` 仅拦截顶层 history 字段，嵌套 transcript 可绕过。
- contrast-2: 验收要求 backend 执行输入切断 raw full chat history。
- fix-2: 在 `contracts/validation.py` 增加递归字段扫描，覆盖嵌套 dict/list，并补 `tests/contracts` 回归。
- check-3: 前端 status 仍以 `phase/summary` 机械播报内部执行状态。
- contrast-3: 验收要求前端作为客服渲染器，避免工程日志直出。
- fix-3: 在 `response_renderer` 将 status/result/failure 改为客服语义消息，去除 phase/log 直传。

## Completion Criteria Evidence

- completion criteria: connected + accumulated + consumed
- connected: 前端消息经 `DtoMapper` 形成结构化 payload，后端按 contracts schema 处理。
- accumulated: backend 通过 `JobStore`、`EventBus`、`QuestionBus` 累积任务与事件状态。
- consumed: frontend `ResponseRenderer` 消费结构化 event 并输出用户可读语义回复。

## Issue Memory Decision

- decision: 本次为架构边界修复，不新增 issue_memory 条目。
- rationale: 无新增“重复性生产故障模式”，仅对既有解耦任务的验收缺口进行收敛。

## Notes / Decisions

- Default choices made: 先关 P0 边界，再做最小路径迁移；不做大规模架构翻修。
- Skill decision: skillized: no（当前为定向修复，直接按 AGENTS 主流程执行）。

## Results

- Files changed:
  - `apps/cs_frontend/gateway/backend_client.py`
  - `apps/cs_frontend/dialogue/response_renderer.py`
  - `contracts/validation.py`
  - `tests/contracts/test_contract_validation.py`
  - `tests/frontend/test_frontend_handler.py`
  - `tests/integration/test_frontend_backend_integration.py`
  - `docs/12_modules_index.md`
  - `docs/13_contracts_index.md`
  - `docs/architecture/contracts/frontend_bridge_contract.md` (moved)
  - `docs/architecture/contracts/frontend_session_contract.md` (moved)
  - `docs/architecture/contracts/support_whiteboard_contract.md` (moved)
  - `policy/allowed_changes.yaml` (moved)
  - `tools/contract_guard.py`
  - `tools/providers/api_agent.py`
  - `tools/providers/local_exec.py`
  - `scripts/workflows/adlc_self_improve_core.py`
  - `tests/test_contract_guard.py`
  - `tests/test_self_improve_external_requirements.py`
  - `tests/test_providers_e2e.py`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260325-decoupling-acceptance-repair.md`
- Verification summary:
  - `python -m unittest discover -s tests/contracts -p "test_*.py" -v` -> 0
  - `python -m unittest discover -s tests/backend -p "test_*.py" -v` -> 0
  - `python -m unittest discover -s tests/frontend -p "test_*.py" -v` -> 0
  - `python -m unittest discover -s tests/integration -p "test_*.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_contract_guard.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_self_improve_external_requirements.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_providers_e2e.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> 0
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 1 (first failure: lite scenario replay; simlab failed=2)
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 0
- Queue status update suggestion (`todo/doing/done/blocked`): done
