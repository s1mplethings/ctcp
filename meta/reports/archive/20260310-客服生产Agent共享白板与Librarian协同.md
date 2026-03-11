# Update 2026-03-10 - 客服+生产Agent共享白板与Librarian协同

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/10_team_mode.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_dispatch.py`
- `tools/providers/manual_outbox.py`
- `tools/providers/api_agent.py`
- `tools/local_librarian.py`
- `tests/test_provider_selection.py`
- `tests/test_api_agent_templates.py`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`

### Plan
1) 先写 queue/CURRENT（task truth + integration check），再做代码实现。
2) 在 dispatch 层增加 shared whiteboard 读写、librarian 检索和 request 注入。
3) 在 `manual_outbox` / `api_agent` prompt 注入 whiteboard snapshot。
4) 增加最小回归测试验证 dispatch 接线和 prompt 消费。
5) 执行 targeted tests + triplet guard + canonical verify 并记录首个失败点。

### Changes
- `meta/backlog/execution_queue.json`
  - 新增 `ADHOC-20260310-support-production-librarian-whiteboard` 队列项（DoD/产物/测试门禁）。
- `meta/tasks/CURRENT.md`
  - 新增本轮 Task Truth / Analysis / Integration Check / Plan / Results。
- `scripts/ctcp_dispatch.py`
  - 增加 shared whiteboard helper：加载、净化、保存、日志、快照。
  - 在 `dispatch_once` 中新增“dispatch request -> librarian lookup -> dispatch result”白板回写闭环。
  - 将 `whiteboard` 上下文（path/query/hits/snapshot）注入 provider request。
  - 复用 `artifacts/support_whiteboard.json` 作为 support+production 共用白板真源。
- `tools/providers/manual_outbox.py`
  - prompt 增加 `Shared-Whiteboard` 段，包含 query/hits/snapshot tail。
- `tools/providers/api_agent.py`
  - prompt 增加 `# WHITEBOARD` 段，包含 query/hits/snapshot tail。
- `tests/test_provider_selection.py`
  - 新增白板 request 注入回归（api provider 路径）。
  - 新增 manual outbox prompt 包含 whiteboard 上下文回归。
- `tests/test_api_agent_templates.py`
  - 新增 API prompt 含 whiteboard snapshot 渲染回归。

### Verify
- `python -m py_compile scripts/ctcp_dispatch.py tools/providers/manual_outbox.py tools/providers/api_agent.py tests/test_provider_selection.py tests/test_api_agent_templates.py` => `0`
- `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
  - first failure gate: `workflow gate (workflow checks)`
  - first failure detail: `changes detected but meta/reports/LAST.md was not updated`
  - minimal fix strategy: 更新 `meta/reports/LAST.md` 后复跑 canonical verify，继续定位下游首个 gate 结果。
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（rerun after report update）=> `0`
  - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-182611` (`passed=14 failed=0`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST sync）=> `0`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-183059` (`passed=14 failed=0`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（ultimate recheck after final report sync）=> `0`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-183547` (`passed=14 failed=0`)

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`（Update 2026-03-10 - 客服+生产Agent共享白板与Librarian协同）
- Shared whiteboard artifact (support + production): `${run_dir}/artifacts/support_whiteboard.json`
- Whiteboard log: `${run_dir}/artifacts/support_whiteboard.md`
- Dispatch/runtime entry:
  - `scripts/ctcp_dispatch.py::dispatch_once`
  - `tools/providers/manual_outbox.py::_render_prompt`
  - `tools/providers/api_agent.py::_render_prompt`

### Integration Proof
- upstream: orchestrator dispatch trigger -> `ctcp_dispatch.dispatch_once`.
- current_module: dispatch whiteboard exchange helpers + provider prompt whiteboard rendering.
- downstream: provider execution consumes whiteboard context and writes target artifact for orchestrator gate advance.
- source_of_truth: `${run_dir}/artifacts/support_whiteboard.json`.
- fallback: `local_librarian.search` 失败时只记录 whiteboard note，不阻断 dispatch 执行。
- acceptance_test:
  - `test_provider_selection.py::test_dispatch_once_injects_shared_whiteboard_context_for_api_provider`
  - `test_provider_selection.py::test_manual_outbox_prompt_contains_shared_whiteboard_context`
  - `test_api_agent_templates.py::test_render_prompt_includes_whiteboard_snapshot`
  - triplet guard tests（runtime_wiring/issue_memory/skill_consumption）
- forbidden_bypass:
  - 仅在 prompt 声明“已协同”但不写 whiteboard artifact。
  - 生产链路不消费 whiteboard snapshot。
  - 新建并行白板导致 support 与 production 上下文分裂。
- user_visible_effect: 客服与生产 agent 在同一 whiteboard/librarian 语境协作，需求和执行上下文衔接更连续。

