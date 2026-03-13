# Current Task

> Archived from `meta/tasks/CURRENT.md` on 2026-03-12.

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260312-support-to-production-path-tests.md`](20260312-support-to-production-path-tests.md)
- Date: 2026-03-12
- Topic: support 到 production run 的渐进式链路测试
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260312-support-to-production-path-tests`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now?
  用户要求“从简单到复杂”验证程序从客服入口到项目生产代码路径是否通畅。仓库里已有 support wiring 回归，但它们分散在 humanization/runtime contract 测试里，缺少一组按阶段命名、直接证明 `support -> bridge -> production artifacts` 的渐进式测试。
- Dependency check:
  - `ADHOC-20260312-support-bot-backend-bridge-wiring`: `done`
  - `ADHOC-20260312-support-project-state-grounding-hardening`: `done`
- Scope boundary:
  - 只新增渐进式链路测试与必需的任务/报告证据。
  - 不改 `scripts/ctcp_support_bot.py`、`scripts/ctcp_front_bridge.py`、`scripts/ctcp_dispatch.py`、`scripts/ctcp_orchestrate.py` 的 runtime 语义。
  - 不扩成 provider、Telegram、prompt 或前端文案重构任务。

## Task Truth Source (single source for current task)

- task_purpose:
  新增一组从简单到复杂的 executable tests，明确验证 `scripts/ctcp_support_bot.py::process_message` 经过 `scripts/ctcp_front_bridge.py` 写入和读取 production run artifacts，再回到 customer-facing support reply 的链路是通的。
- allowed_behavior_change:
  - 可新增 `tests/test_support_to_production_path.py`，按 level 组织 simple -> medium -> complex 路径证明。
  - 可更新 `meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 及对应 archive 文件记录此次测试任务与证据。
  - 可在测试里 mock subprocess / provider 边界，但必须尽量复用真实 `ctcp_front_bridge` / `ctcp_dispatch` / `ctcp_support_bot` 代码路径。
- forbidden_goal_shift:
  - 不得为了让测试更容易写而改 runtime 语义。
  - 不得把这次任务扩大成新的 support 功能修复、桥接重构或 orchestrator 重写。
  - 不得只写说明文档或 prompt 描述，必须落成可执行测试。
- in_scope_modules:
  - `tests/test_support_to_production_path.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260312-support-to-production-path-tests.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260312-support-to-production-path-tests.md`
- out_of_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `frontend/conversation_mode_router.py`
  - `frontend/response_composer.py`
  - 与本次渐进式链路测试无关的其他未提交工作树改动
- completion_evidence:
  - Level 1 测试证明 bridge 会把 support turn 写进 `artifacts/support_frontend_turns.jsonl` 与 `artifacts/support_whiteboard.json`。
  - Level 2 测试证明 support context 会从 `RUN.json`、`artifacts/frontend_request.json`、`artifacts/support_whiteboard.json` 读取 production truth。
  - Level 3/4 测试证明 `process_message()` 能创建或绑定 run、记录 support turn、推进 bridge helper，并把结果落成 `artifacts/support_reply.json`，且后续状态查询复用同一个 run。
  - targeted suite、triplet guard、workflow gate、canonical verify 留下证据，并显式满足 `connected + accumulated + consumed`。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户入口仍是 `scripts/ctcp_support_bot.py::process_message`；新测试也会直接从这个 entrypoint 驱动复杂路径。
- Downstream consumer analysis:
  - support turn 经 `sync_project_context()` 进入 `scripts/ctcp_front_bridge.py::{ctcp_new_run, ctcp_record_support_turn, ctcp_get_support_context, ctcp_advance}`，由 `scripts/ctcp_dispatch.py` 写共享 whiteboard，再由 `build_final_reply_doc()` 产出 customer-visible `artifacts/support_reply.json`。
- Source of truth:
  - support session `artifacts/support_session_state.json`
  - production run `RUN.json`
  - production run `artifacts/frontend_request.json`
  - production run `artifacts/support_frontend_turns.jsonl`
  - production run `artifacts/support_whiteboard.json`
  - support session `artifacts/support_reply.json`
- Current break point / missing wiring:
  - 现有测试更多是点状回归，很多复杂路径直接 mock 掉 bridge helper，缺少一组明确分层的“support 到 production”路径证明。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `tests/test_support_to_production_path.py` driving real `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, and `scripts/ctcp_dispatch.py` code paths
- downstream:
  `process_message()` -> `sync_project_context()` -> `ctcp_front_bridge` helpers -> production `frontend_request/support_frontend_turns/support_whiteboard` artifacts -> `build_final_reply_doc()` -> support session `artifacts/support_reply.json`
- source_of_truth:
  support session `artifacts/support_session_state.json` plus production `RUN.json`, `artifacts/frontend_request.json`, `artifacts/support_frontend_turns.jsonl`, `artifacts/support_whiteboard.json`
- fallback:
  若渐进式测试发现某一级断路，应在该级 first failure 停住并修最小测试边界；不得跳过 bridge、不得伪造 production truth、不得只保留 chat-memory 级验证
- acceptance_test:
  - `python -m py_compile tests/test_support_to_production_path.py`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 只断言 mock 被调用，而不检查 production artifacts
  - 绕过 `ctcp_front_bridge` 直接在 support test 里伪造 run 状态
  - 省略 support reply artifact 或 bound-run reuse 证明
- user_visible_effect:
  - 仓库拥有一组可直接运行的 staged tests，能明确告诉你客服入口到底有没有真正接上 production run。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: 渐进式测试在简单级证明 bridge 会写 support_frontend_turns 与 support_whiteboard 产物
- [x] DoD-2: 渐进式测试在中等级证明 support context 读取 RUN/frontend_request/whiteboard 的 production truth
- [x] DoD-3: 渐进式测试在复杂级证明 support entrypoint 能 create/bind run、record support turn、advance bridge helper 并写出 support_reply artifact
- [x] DoD-4: targeted regressions、triplet guard、workflow gate、canonical verify 留下 `connected + accumulated + consumed` 证据

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git diff` generated; no destructive operations used)
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 绑定 `support-to-production-path-tests` task，并把 integration proof 锁到 support entrypoint -> bridge -> production artifacts -> support reply 这条链。
2) 先更新 queue / CURRENT / LAST / archive，明确这是 tests-only 任务和 simple-to-complex DoD。
3) 在 `tests/test_support_to_production_path.py` 新增 4 个 level 测试：
   - level 1: bridge 写 production artifacts
   - level 2: bridge 读 production truth
   - level 3: support entrypoint create/bind + advance
   - level 4: bound status query 复用同一个 production run
4) Local check / contrast / fix loop:
   - `python -m py_compile tests/test_support_to_production_path.py`
   - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
   - record first failure and minimal fix strategy if anything breaks
5) Canonical verify gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
6) Completion criteria: prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made:
  - 复用真实 `ctcp_front_bridge` / `ctcp_dispatch` / `ctcp_support_bot` 代码，只 mock subprocess/provider 边界，避免把路径全部 mock 空。
- Alternatives considered:
  - 把新覆盖继续塞进 `tests/test_runtime_wiring_contract.py`；拒绝，因为用户要的是“从简单到复杂”的独立 staged suite，单独文件更清晰。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision:
  - 本次任务只加 coverage，没有发现新的 recurring defect；暂不新增 problem registry 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`):
  - skillized: no, because this is repository-local regression coverage for one support-to-production wiring path, not a reusable runtime workflow asset.

## Results

- Files changed:
  - `tests/test_support_to_production_path.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260312-support-to-production-path-tests.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260312-support-to-production-path-tests.md`
- Verification summary:
  - `python -m py_compile tests/test_support_to_production_path.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` => first run `1`
    - first failure point: `test_level2_bridge_reads_production_truth_back_into_support_context`
    - failure detail: fake orchestrate fixture did not seed `artifacts/frontend_request.json`, so `ctcp_get_support_context()` returned empty `frontend_request.goal`
    - minimal fix strategy: seed `frontend_request.json` inside the fake orchestrate harness in `tests/test_support_to_production_path.py`, then rerun the staged suite
  - `python -m py_compile tests/test_support_to_production_path.py` => second run `0`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` => second run `0` (4 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (12 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite, workflow_gate, plan_check, patch_check, behavior_catalog_check, contract_checks, doc_index_check, triplet_guard, lite_replay, python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-202149` (`passed=14 failed=0`)
    - python unit test summary: `155 passed, 3 skipped`
- Queue status update suggestion (`todo/doing/done/blocked`):
  - done
