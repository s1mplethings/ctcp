# Update 2026-03-09 - Single-Purpose / Single-Flow / Single-Responsibility Refactor

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/04_execution_flow.md`
- `docs/05_agent_mode_matrix.md`
- `docs/10_workflow.md`
- `docs/10_team_mode.md`
- `docs/adlc_pipeline.md`
- `docs/22_teamnet_adlc.md`
- `docs/25_project_plan.md`
- `AGENTS.md`
- `README.md`
- `ai_context/00_AI_CONTRACT.md`
- `meta/tasks/TEMPLATE.md`
- `meta/templates/integration_check.md`
- `scripts/workflow_checks.py`
- `scripts/sync_doc_links.py`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`

### Plan
1) 新建单一 repo purpose 文档、单一 canonical flow 文档、mode/responsibility 矩阵文档。
2) 收敛已有 overview/workflow/team 文档为 lane/scope 文档，避免重复定义仓库目的和主流程。
3) 强化 `AGENTS.md`：行动前三重识别 + 冲突停机；流程语义改为引用 canonical flow 源。
4) 强化 `meta/tasks/TEMPLATE.md` 与 `scripts/workflow_checks.py`，将 current-task truth 字段变成硬门禁。
5) 执行 check/contrast/fix loop，再跑 canonical verify 并记录首个失败点。

### Changes
- New single-purpose/single-flow docs:
  - `docs/01_north_star.md`
  - `docs/04_execution_flow.md`
  - `docs/05_agent_mode_matrix.md`
- Source-map and scope-boundary refactor:
  - `docs/00_CORE.md`（runtime truth boundary + source map）
  - `docs/02_workflow.md`（reclassify as runtime execution-lane doc, non-canonical for repo workflow）
  - `docs/00_overview.md`, `docs/10_workflow.md`, `docs/10_team_mode.md`（明确 lane/scope 边界）
  - `docs/adlc_pipeline.md`, `docs/22_teamnet_adlc.md`（补充 scope boundary，避免与 canonical flow 竞争）
  - `docs/25_project_plan.md`（明确 CURRENT 为 current-task truth source）
  - `README.md`（authoritative source map）
- Agent/task control hardening:
  - `AGENTS.md`（preflight triple-source identification + stop-on-conflict + canonical flow reference）
  - `meta/tasks/TEMPLATE.md`（新增 task truth 字段）
  - `scripts/workflow_checks.py`（新增 task truth 字段门禁）
  - `meta/backlog/execution_queue.json`（新增 ADHOC queue item）
  - `meta/tasks/CURRENT.md`（新增本轮 task truth/analysis/integration/plan 记录）
- Index sync:
  - `scripts/sync_doc_links.py`（curated docs 增补 new canonical docs）
  - `README.md` doc index 自动同步

### Verify
- `python scripts/workflow_checks.py` => exit `0`
- `python scripts/sync_doc_links.py --check` => exit `0`
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => exit `0` (5 passed)
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => exit `0` (3 passed)
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => exit `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-201914/summary.json`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: include assertion failed (`missing expected text: failure_bundle.zip`)
    - `S16_lite_fixer_loop_pass`: `expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused)
  - 对齐 S15 include 断言与当前 failure bundle 提示文案。
  - 对齐 S16 fixture patch 与当前 README 基线。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Queue: `meta/backlog/execution_queue.json`
- Canonical purpose/flow docs:
  - `docs/01_north_star.md`
  - `docs/04_execution_flow.md`
- Runtime truth contract:
  - `docs/00_CORE.md`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-201914/summary.json`

