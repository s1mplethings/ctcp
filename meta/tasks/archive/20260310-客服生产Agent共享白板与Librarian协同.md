# Update 2026-03-10 - 客服+生产Agent共享白板与Librarian协同

### Queue Binding
- Queue Item: `ADHOC-20260310-support-production-librarian-whiteboard`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 让客服与所有生产执行 agent 在同一 whiteboard 上共享 librarian 检索线索，形成“支持侧提问 -> 生产侧执行 -> 结果回写”的闭环协作。
- Scope:
  - 在 dispatch 链路增加白板读写与 librarian 线索注入。
  - 把白板快照注入生产 provider prompt（manual_outbox + api_agent）。
  - 与现有 `support_whiteboard` 工件复用，避免 support/production 上下文分裂。
  - 增加最小回归测试覆盖 dispatch 白板接线和 prompt 注入。
- Out of scope:
  - orchestrator 状态机语义变更。
  - frontend bridge 能力扩展。
  - 新外部依赖引入。

### Task Truth Source (single source for current task)

- task_purpose: 把生产 agent（chair/librarian/guardian/cost_controller/researcher/patchmaker/fixer）的派发执行接线到共享 whiteboard + librarian 协同上下文，并与客服通道共用同一白板真源。
- allowed_behavior_change:
  - `scripts/ctcp_dispatch.py` 增加 shared whiteboard state 读写、librarian 查询和 request 注入。
  - `tools/providers/manual_outbox.py` 与 `tools/providers/api_agent.py` prompt 注入 whiteboard snapshot 与 librarian hits。
  - 使用 `artifacts/support_whiteboard.json` 作为 shared whiteboard truth source（生产侧与客服侧共用）。
  - 增补 `tests/test_provider_selection.py`、`tests/test_api_agent_templates.py` 回归用例。
- forbidden_goal_shift:
  - 不得绕过 dispatch/provider 主链路新增并行执行路径。
  - 不得改变 verify 入口或 gate 语义。
  - 不得向用户回复泄露内部路径/日志细节。
- in_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/manual_outbox.py`
  - `tools/providers/api_agent.py`
  - `tests/test_provider_selection.py`
  - `tests/test_api_agent_templates.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `frontend/*`
  - `src/` / `include/`
  - `tools/telegram_cs_bot.py`（本轮仅复用其 whiteboard 工件）
- completion_evidence:
  - dispatch 执行后在 run_dir 写入共享 whiteboard 条目（agent request + librarian hit + execution result）。
  - manual_outbox/api_agent prompt 含 whiteboard snapshot。
  - targeted tests + triplet guard 通过，canonical verify 执行并记录结果。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 生产链路入口是 `scripts/ctcp_dispatch.py::dispatch_once`，由 orchestrator blocked/fail gate 触发。
- Downstream consumer analysis:
  - `manual_outbox` / `api_agent` 读取 request 并生成目标 artifact；后续由 orchestrator 消费产物推进状态机。
- Source of truth:
  - 共享白板真源为 `${run_dir}/artifacts/support_whiteboard.json`。
  - librarian 检索来自 repo-local `tools.local_librarian.search`。
- Current break point / missing wiring:
  - 现有白板+librarian 只在客服 support turn，生产 dispatch 没有接线，导致支持侧与执行侧上下文断开。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: orchestrator dispatch trigger -> `ctcp_dispatch.dispatch_once`.
- current_module: shared whiteboard helpers in `ctcp_dispatch` + provider prompt rendering in `manual_outbox`/`api_agent`.
- downstream: provider prompt consumption -> target artifact generation -> orchestrator gate advance.
- source_of_truth: `${run_dir}/artifacts/support_whiteboard.json`.
- fallback: `local_librarian` 不可用或检索异常时仅记录 agent whiteboard note，不阻断 dispatch 执行。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 在 prompt 文本宣称已协同但不写 whiteboard artifact。
  - 仅客服侧白板，生产链路不消费。
  - provider 执行不读取 whiteboard snapshot。
- user_visible_effect:
  - 客服与生产 agent 共享同一 librarian/whiteboard 语境，减少重复追问与上下文断裂。
  - 生产 prompt 可直接看到 support 与 librarian 的最新协作记录。

### DoD Mapping (from request)

- [x] DoD-1: dispatch 写入生产 agent request/result 到共享 whiteboard，并挂接 librarian 线索。
- [x] DoD-2: manual_outbox 与 api_agent prompt 注入 whiteboard snapshot/librarian hits。
- [x] DoD-3: 共享白板与客服通道复用同一路径，不再 support/production 分裂。
- [x] DoD-4: targeted regression + triplet guard 通过。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 在 `ctcp_dispatch` 增加 whiteboard state helper，dispatch 前后写入 agent/librarian 交互条目，并把 snapshot 注入 request。
2) 更新 `manual_outbox` prompt 渲染，追加 whiteboard 上下文段。
3) 更新 `api_agent` prompt 渲染，追加 whiteboard 上下文段。
4) 补充 provider/dispatch 相关回归测试。
5) 执行 targeted tests + triplet guard + canonical verify，并回填结果到 CURRENT/LAST。

### Notes / Decisions

- Default choices made: 复用 `artifacts/support_whiteboard.json` 作为共享白板真源，不新建并行白板文件。
- Alternatives considered: 新建 `artifacts/agent_whiteboard.json`；拒绝（会造成客服与生产上下文分叉）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 若出现 whiteboard 注入缺失/用户可见泄漏回归，将在本轮结果中补 issue memory 记录；当前先按无新增故障处理。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository-local runtime wiring refinement and not yet a stable reusable multi-repo skill asset.

### Results (2026-03-10 - support+production shared whiteboard/librarian wiring)

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/manual_outbox.py`
  - `tools/providers/api_agent.py`
  - `tests/test_provider_selection.py`
  - `tests/test_api_agent_templates.py`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m py_compile scripts/ctcp_dispatch.py tools/providers/manual_outbox.py tools/providers/api_agent.py tests/test_provider_selection.py tests/test_api_agent_templates.py` => `0`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-182611` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-183059` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（ultimate recheck after final report sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-183547` (`passed=14 failed=0`)

- Queue status update suggestion (`todo/doing/done/blocked`): `done` (shared whiteboard+librarian wiring for support+production completed and verified).

