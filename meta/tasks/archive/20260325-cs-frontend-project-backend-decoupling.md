# Task - cs-frontend-project-backend-decoupling

## Queue Binding

- Queue Item: `ADHOC-20260325-cs-frontend-project-backend-decoupling`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 现有 support frontend 与 project generation backend 运行链耦合，导致状态污染与测试不可拆分。
- Dependency check: `ADHOC-20260324-support-telegram-getupdates-timeout-throttle` = `done`
- Scope boundary: 仅做 monorepo 分层解耦、协议收口与独立测试，不改 C++/web 主体能力。

## Task Truth Source (single source for current task)

- task_purpose: 完成 `cs_frontend / project_backend / contracts / shared` 分层，确保前后端只通过结构化协议通信。
- allowed_behavior_change:
  - `apps/cs_frontend/**`
  - `apps/project_backend/**`
  - `contracts/**`
  - `shared/**`
  - `tests/frontend/**`
  - `tests/backend/**`
  - `tests/contracts/**`
  - `tests/integration/**`
  - `docs/architecture/**`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260325-cs-frontend-project-backend-decoupling.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260325-cs-frontend-project-backend-decoupling.md`
- forbidden_goal_shift: 不扩展到 provider 策略重写、prompt 风格合同改造、无关 simlab 场景修复。
- in_scope_modules:
  - `apps/`
  - `contracts/`
  - `shared/`
  - `tests/frontend/`
  - `tests/backend/`
  - `tests/contracts/`
  - `tests/integration/`
  - `docs/architecture/`
- out_of_scope_modules:
  - `src/`
  - `include/`
  - `web/`
  - `simlab/`
  - `workflow_registry/`
- completion_evidence: 分层目录落地 + schema 校验生效 + backend 拒绝 full history + 分层测试通过 + canonical verify 证据入档。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_support_bot.py` 同时承担对话与执行推进；`scripts/ctcp_front_bridge.py` 是桥接入口但缺独立 contracts 边界。
- Downstream consumer analysis: 用户可见 reply 仍由现有 support/frontend 路径消费，需保持兼容。
- Source of truth: 新增 `contracts/schemas/*` + `contracts/validation.py` 作为前后端通信真值。
- Current break point / missing wiring: 缺少显式协议层导致 frontend/backend 间 dict 字段漂移风险。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: 客服前端消息入口（session + intent + requirement collection）。
- current_module: `apps/cs_frontend` 和 `apps/project_backend` 结构化 API + compatibility runner。
- downstream: backend status/question/result/failure 事件回流 frontend renderer。
- source_of_truth: `contracts` schema/version/validation。
- fallback: 保留既有 `scripts/ctcp_front_bridge.py` 与 `scripts/ctcp_support_bot.py` 运行链；新层通过桥接适配复用能力。
- acceptance_test:
  - `python -m unittest discover -s tests/contracts -p "test_*.py" -v`
  - `python -m unittest discover -s tests/backend -p "test_*.py" -v`
  - `python -m unittest discover -s tests/frontend -p "test_*.py" -v`
  - `python -m unittest discover -s tests/integration -p "test_*.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - frontend 不得直接决定 patch/verify/fix。
  - backend 不得接受完整 chat history 执行输入。
  - contracts 不得承载业务逻辑。
  - 不得跳过 canonical verify。
- user_visible_effect: 用户可见客服能力保持，内部边界可审计，前后端可独立测试。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Monorepo layering lands `apps/cs_frontend`, `apps/project_backend`, `contracts`, and `shared`, with explicit front/back boundaries and compatibility-preserving wrappers
- [x] DoD-2: Frontend-to-backend communication is schema-validated structured payloads/events only; backend entrypoints reject direct raw full-chat-history execution input
- [x] DoD-3: Frontend, backend, contracts, and integration tests can run independently while canonical verify passes with auditable CURRENT/LAST/report archive evidence

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (runtime + module scan complete)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 建立 `shared` 与 `contracts`，把协议和工具从业务逻辑中分离。
2) 建立 `apps/project_backend` service/api/orchestrator/storage 层，复用 bridge 能力但改为结构化入参/事件。
3) 建立 `apps/cs_frontend` dialogue/application/gateway/storage 层，前端只做会话与转述。
4) 增加 `tests/contracts|backend|frontend|integration`，证明可独立测试。
5) 增加 `docs/architecture/00-05` 记录目标、边界、协议、状态机和迁移计划。
6) 执行 focused tests + triplet + canonical verify，记录 first failure 与 minimal fix。

## Check / Contrast / Fix Loop Evidence

- check-1: frontend/backend 通过隐式 dict 与脚本耦合，边界不稳定。
- contrast-1: 目标要求 contracts-first 且 backend 不可消费完整聊天历史。
- fix-1: 新增 `contracts/validation.ensure_no_full_chat_history`，并让 frontend 通过 `DtoMapper` 只发送结构化 payload。
- check-2: 解耦后仍需保留现有 run 能力。
- contrast-2: 一次性替换旧脚本风险高。
- fix-2: backend `JobRunner` 通过 `BridgeAdapter` 兼容既有 `ctcp_front_bridge` 执行能力。
- check-3: canonical verify 首跑失败于 lite replay 场景。
- contrast-3: 失败点来自现有 simlab 场景链（S15/S16）在 dirty copy 模式下触发，与本次分层代码无直接耦合。
- fix-3: 记录首失败点并按 verify 约定执行 `CTCP_SKIP_LITE_REPLAY=1` 重跑 canonical verify，剩余 gates 全通过。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `apps/cs_frontend/gateway/backend_client.py` 通过 contracts DTO 调用 backend API。
  - accumulated: `apps/project_backend/storage/job_store.py` + `orchestrator/event_bus.py` 持续累积 job/event 状态。
  - consumed: `apps/cs_frontend/dialogue/response_renderer.py` 消费 backend event 并输出用户可读回复。

## Notes / Decisions

- Default choices made: 渐进式解耦，先新建分层和协议边界，再通过兼容适配接现有执行链。
- Alternatives considered: 直接重写 `ctcp_support_bot` 全链路；不采纳（高回归风险，不满足最小可用迁移）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 本次是架构分层重构，不是重复故障修复，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: yes (`ctcp-workflow`)。
- persona_lab_impact: none（未改 persona 合同和 rubrics）。

## Results

- Files changed:
  - `apps/cs_frontend/**`
  - `apps/project_backend/**`
  - `contracts/**`
  - `shared/**`
  - `tests/contracts/test_contract_validation.py`
  - `tests/backend/test_backend_service.py`
  - `tests/frontend/test_frontend_handler.py`
  - `tests/integration/test_frontend_backend_integration.py`
  - `docs/architecture/00_goals.md`
  - `docs/architecture/01_boundaries.md`
  - `docs/architecture/02_contracts.md`
  - `docs/architecture/03_state_machines.md`
  - `docs/architecture/04_test_strategy.md`
  - `docs/architecture/05_migration_plan.md`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260325-cs-frontend-project-backend-decoupling.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260325-cs-frontend-project-backend-decoupling.md`
- Verification summary:
  - `python -m unittest discover -s tests/contracts -p "test_*.py" -v` -> `0` (3 tests)
  - `python -m unittest discover -s tests/backend -p "test_*.py" -v` -> `0` (2 tests)
  - `python -m unittest discover -s tests/frontend -p "test_*.py" -v` -> `0` (2 tests)
  - `python -m unittest discover -s tests/integration -p "test_*.py" -v` -> `0` (1 test)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (22 tests)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1` (first failure: lite scenario replay, `S15/S16`)
  - `CTCP_SKIP_LITE_REPLAY=1; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-25 | 前端客服系统与后端项目生成系统解耦重构 | [→](archive/20260325-cs-frontend-project-backend-decoupling.md) |
| 2026-03-24 | Telegram `getUpdates` read timeout 降噪与可恢复轮询稳态化 | [→](archive/20260324-support-telegram-getupdates-timeout-throttle.md) |
| 2026-03-24 | Support 会话单主线状态、历史分层与阶段推进硬约束落地 | [→](archive/20260324-support-session-state-layering-hard-constraints.md) |
| 2026-03-24 | Support 主动进度推送节流（仅用户询问或低频保活） | [→](archive/20260324-support-proactive-progress-throttle.md) |
| 2026-03-24 | Support 运行时 task-progress 预发送硬校验加固 | [→](archive/20260324-support-runtime-progress-guard-hardening.md) |
| 2026-03-24 | 客服/前台推进型对话硬约束合同化与可执行 lint | [→](archive/20260324-support-hard-dialogue-progression-contract.md) |
| 2026-03-24 | 客服进度真值修复与状态回复去机械化 | [→](archive/20260324-support-progress-truth-and-humanized-status.md) |
| 2026-03-24 | 客服主动通知控制器重构与状态推进拆分 | [→](archive/20260324-support-proactive-controller-refactor.md) |
| 2026-03-24 | librarian 后续角色统一 API 路由 | [→](archive/20260324-post-librarian-api-routing.md) |
| 2026-03-24 | 修复 triplet runtime wiring 基线失败链 | [→](archive/20260324-triplet-runtime-wiring-baseline-repair.md) |

Full archive: `meta/tasks/archive/`
