# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260311-support-bot-humanization-verify-blocker.md`](archive/20260311-support-bot-humanization-verify-blocker.md)
- Date: 2026-03-11
- Topic: 收口 support-bot humanization verify blocker
- Status: `done` (support-bot regressions fixed; canonical verify passed)

## Queue Binding

- Queue Item: `ADHOC-20260311-support-bot-humanization-verify-blocker`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now?
  backend hard-local role patch 已经完成，本仓库 canonical verify 的首个剩余失败点只剩 3 个 support-bot humanization regression。
- Dependency check:
  - `ADHOC-20260311-boundary-first-support-expression`: `done`
  - `ADHOC-20260311-frontend-md-scope-validation`: `done`
  - `ADHOC-20260311-telegram-run-provider-alignment`: `done`
- Scope boundary:
  - 只修 support/customer-facing reply shaping 与相关 frontend rendering fallback，不改 dispatcher/orchestrator/provider routing。

## Task Truth Source (single source for current task)

- task_purpose: 收口 canonical verify 当前剩余的 support-bot humanization failures，让 bare project creation/new-run 与项目详情低信号回复继续遵守 CTCP frontend boundary：优先当前详细 requirement，避免 internal marker 外泄，必要时才追问高杠杆问题。
- allowed_behavior_change:
  - `tools/telegram_cs_bot.py` 可调整 bare project creation kickoff fallback、new-run local ack、customer reply shaping。
  - `frontend/response_composer.py` 可调整项目态 raw reply 的保留条件，让低信号或带 internal marker 的文本回到 frontend-reviewed PM reply。
  - `tests/test_support_bot_humanization.py`、`tests/test_frontend_rendering_boundary.py` 可补最小 regression。
  - `ai_context/problem_registry.md` 可记录这次用户可见回复回退失真。
  - `meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录本轮证据。
- forbidden_goal_shift:
  - 不得把这轮扩成 Telegram/support-bot 全量文案重写。
  - 不得放宽 frontend/customer-facing boundary 去直接暴露 backend raw failure/internal marker。
  - 不得改 provider selection、whiteboard wiring、orchestrator state machine 来绕过当前回复问题。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `frontend/response_composer.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `tools/providers/*`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
- completion_evidence:
  - bare project creation / mojibake fallback 的用户可见回复会明确请求项目目标、输入与期望结果，而不是只回显泛化项目请求。
  - `support_turn_local` 在已有详细 requirement 时，不再把 `missing runtime_target` 或泛化旧问题原样吐给用户，而会走 frontend-reviewed PM reply，并优先当前详细 requirement source。
  - targeted support/frontend regressions、triplet guard、canonical verify 通过。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - Telegram 绑定会话入口在 `tools/telegram_cs_bot.py::_handle_message`，会分流到 `_create_run`（新目标）或 `_send_customer_reply`（support turn）。
- Downstream consumer analysis:
  - `_send_customer_reply` 把 `raw_backend_state`、`task_summary`、`raw_reply_text` 交给 `frontend.render_frontend_output`，随后 `build_user_reply_payload` 输出最终 customer-facing 文本。
- Source of truth:
  - 项目创建 kickoff 真源：`tools/telegram_cs_bot.py::_project_kickoff_reply` / `build_employee_note_reply` / `_create_run`。
  - 项目详情 reply shaping 真源：`frontend/response_composer.py::run_internal_reply_pipeline` / `_stage_project_manager_draft`。
- Current break point / missing wiring:
  - 新目标重绑后会直接走 `_create_run` 本地 ack；当前 bare project creation ack 只回显泛化项目请求，没有进入“项目目标/输入/期望结果”的 kickoff。
  - 项目详情 turn 当前总是保留 raw model text；当 raw text 低信号或含 `missing runtime_target` 这类 internal marker 时，会覆盖 frontend-reviewed PM reply，导致 requirement source 选择失真并把内部标记漏给用户。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram text turn -> `_handle_message` -> `_create_run` or `_send_customer_reply`.
- current_module: `tools/telegram_cs_bot.py` + `frontend/response_composer.py`.
- downstream: `build_user_reply_payload()` -> Telegram public send + support session state persistence.
- source_of_truth: `tools/telegram_cs_bot.py`, `frontend/response_composer.py`, `tests/test_support_bot_humanization.py`.
- fallback: low-signal/internal-marker raw project replies 只允许在 greeting/smalltalk 等显式 raw-safe 场景保留；项目创建和项目详情场景应退回 frontend-reviewed customer reply。
- acceptance_test:
  - `python -m py_compile tools/telegram_cs_bot.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_frontend_rendering_boundary.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 只改测试期待，不改运行时代码。
  - 保留 `missing runtime_target` 等 internal marker，再靠后置 sanitize 碰运气。
  - 用泛化旧问题追问替代当前详细 requirement 总结，回避 requirement source 选择问题。
- user_visible_effect:
  - 项目创建 turn 会回到项目 kickoff 语境，而不是只回显“我想做个项目”。
  - 详细项目 turn 会优先反映当前 requirement，而不是被旧历史或 internal marker 带偏。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: bare project creation / new-run kickoff replies ask for project goal, input, and expected result instead of echoing a generic project-creation request
- [x] DoD-2: project-detail reply shaping rewrites low-signal or internal-marker raw replies into frontend-reviewed PM replies that prefer the current detailed requirement source
- [x] DoD-3: targeted support-bot/frontend regressions and canonical verify clear the remaining python unit-test blocker

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [ ] Research logged (if needed): `N/A`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 先补 queue/CURRENT/LAST 摘要，恢复新的 support-bot verify-blocker task truth。
2) 在 `tools/telegram_cs_bot.py` 收紧 bare project creation kickoff / new-run ack。
3) 在 `frontend/response_composer.py` 为项目态增加低信号/internal-marker raw reply 的回退条件。
4) 补最小 regression，验证 detailed requirement source 优先级和 project kickoff 文案。
5) 执行 local check/fix loop：
   - `python -m py_compile tools/telegram_cs_bot.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_frontend_rendering_boundary.py`
   - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
   - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
6) Canonical verify gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
7) Completion criteria: clear remaining verify blocker and record `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made:
  - 先以最小运行时路径修复，不扩大到 prompt/provider/orchestrator 层。
- Alternatives considered:
  - 只在 `build_user_reply_payload` 末端追加更多替换；拒绝，因为根因在项目态 raw reply 的保留条件，而不是最终拼接层。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision:
  - 已记录到 `ai_context/problem_registry.md` Example 5。
- Skill decision (`skillized: yes` or `skillized: no, because ...`):
  - skillized: yes (`ctcp-workflow` + `ctcp-gate-precheck`)。

## Results

- Files changed:
  - `tools/telegram_cs_bot.py`
  - `frontend/response_composer.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/archive/20260311-support-bot-humanization-verify-blocker.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/archive/20260311-support-bot-humanization-verify-blocker.md`
  - `meta/reports/LAST.md`
- Verification summary:
  - `python scripts/workflow_checks.py` => `0`
  - `python -m py_compile tools/telegram_cs_bot.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_frontend_rendering_boundary.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (22 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (26 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-153736` (`passed=14 failed=0`)
    - python unit tests summary: `210 passed, 3 skipped`
- Queue status update suggestion (`todo/doing/done/blocked`):
  - `done`

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-11 | 收口 support-bot humanization verify blocker | [→](archive/20260311-support-bot-humanization-verify-blocker.md) |
| 2026-03-11 | 后端角色分工收紧与本地 Librarian 硬边界 | [→](archive/20260311-backend-role-boundary-local-librarian.md) |
| 2026-03-11 | 前端 MD 范围验证（能力询问本地答复） | [→](archive/20260311-前端-MD-范围验证-能力询问本地答复.md) |
| 2026-03-11 | Telegram 新建 run 的执行 provider 对齐 | [→](archive/20260311-Telegram-新建-run-的执行-provider-对齐.md) |
| 2026-03-11 | 设计目标改为机械层定边界 agent 定表述 | [→](archive/20260311-设计目标改为机械层定边界agent-定表述.md) |
| 2026-03-10 | 客服用户可见通知去机械化统一闸门 | [→](archive/20260310-客服用户可见通知去机械化统一闸门.md) |
| 2026-03-10 | 客服+生产 Agent 共享白板与 Librarian 协同 | [→](archive/20260310-客服生产Agent共享白板与Librarian协同.md) |
| 2026-03-10 | 客服与项目设计流程接线 librarian 白板 | [→](archive/20260310-客服与项目设计流程接线-librarian-白板.md) |
| 2026-03-10 | Markdown 对象状态机治理基线 | [→](archive/20260310-Markdown-对象状态机治理基线-6-file-baseline.md) |
| 2026-03-09 | Frontend control plane + bridge Phase 1-2 | [→](archive/20260309-Frontend-control-plane-single-execution-bridge-Phase-1-2.md) |

Full archive: `meta/tasks/archive/` (49 files)
