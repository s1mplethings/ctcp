# Update 2026-03-09 - Single-Purpose/Single-Flow Operating Model Refactor

### Queue Binding
- Queue Item: `ADHOC-20260309-single-purpose-single-flow-model`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 将仓库重构为单一目的、单一主流程、单一职责分层、单一关注点真相源。
- Scope: contracts/docs/templates/workflow gate 强化；不改业务功能逻辑。
- Out of scope: 产品功能行为扩展与运行时算法重写。

## Task Truth Source (single source for current task)
- task_purpose: 固化 repo purpose / canonical flow / current task scope / runtime truth 的单一来源。
- allowed_behavior_change: 文档契约重构、模板字段扩展、workflow gate 检查强化、verify/docs 索引同步。
- forbidden_goal_shift: 不得将任务扩展为产品需求重设计或前后端新功能开发。
- in_scope_modules: `docs/01_north_star.md`, `docs/04_execution_flow.md`, `docs/05_agent_mode_matrix.md`, `AGENTS.md`, `docs/00_CORE.md`, `docs/00_overview.md`, `docs/02_workflow.md`, `docs/10_workflow.md`, `docs/10_team_mode.md`, `docs/adlc_pipeline.md`, `docs/22_teamnet_adlc.md`, `meta/tasks/TEMPLATE.md`, `scripts/workflow_checks.py`, `scripts/sync_doc_links.py`, `README.md`, `docs/25_project_plan.md`, `ai_context/00_AI_CONTRACT.md`.
- out_of_scope_modules: `src/`, `frontend/` 业务实现逻辑、`scripts/ctcp_orchestrate.py` 运行态算法。
- completion_evidence: workflow checks + triplet guard + canonical verify 结果 + LAST 报告证据。

## Analysis / Find (before plan)
- Entrypoint analysis: agent 行为入口受 `AGENTS.md` 与 `docs/04_execution_flow.md` 约束。
- Downstream consumer analysis: `scripts/workflow_checks.py` 与 `scripts/verify_repo.*` 是执行层硬门禁消费端。
- Source of truth: repo purpose=`docs/01_north_star.md`; flow=`docs/04_execution_flow.md`; current task=`meta/tasks/CURRENT.md`; runtime truth=`docs/00_CORE.md`。
- Current break point / missing wiring: 多文档重复定义 purpose/flow，CURRENT 缺少显式 task truth 字段，容易中途 goal drift。
- Repo-local search sufficient: `yes`
- External research artifact: `N/A`

## Integration Check (before implementation)
- upstream: `AGENTS.md` preflight + canonical flow references
- current_module: `docs/01_north_star.md`, `docs/04_execution_flow.md`, `scripts/workflow_checks.py`
- downstream: `scripts/verify_repo.ps1/.sh` + `meta/reports/LAST.md`
- source_of_truth: `docs/01_north_star.md` / `docs/04_execution_flow.md` / `meta/tasks/CURRENT.md` / `docs/00_CORE.md`
- fallback: 若历史文档仍需保留，仅允许降级为 lane/subsystem 文档并显式声明非 canonical
- acceptance_test: `python scripts/workflow_checks.py` + triplet tests + `scripts/sync_doc_links.py --check` + `scripts/verify_repo.ps1`
- forbidden_bypass: 跳过 task truth 字段、在 AGENTS/README 静默改目的、只改 prompt 不改门禁
- user_visible_effect: 未来 agent 更容易识别唯一目的/流程/任务边界，减少实现中途改目标。

## DoD Mapping (from request)
- [x] DoD-1: 新增单一 repo purpose 文档 `docs/01_north_star.md`。
- [x] DoD-2: 新增单一 canonical flow 文档 `docs/04_execution_flow.md`。
- [x] DoD-3: 新增 mode/responsibility 矩阵 `docs/05_agent_mode_matrix.md`。
- [x] DoD-4: 收敛旧 overview/workflow 文档为 lane/scope 文档并标注非 canonical。
- [x] DoD-5: `AGENTS.md` 增加三重识别和冲突停机规则。
- [x] DoD-6: `meta/tasks/TEMPLATE.md` 与 workflow gate 增加 task truth 字段。
- [x] DoD-7: 明确 runtime truth 只来自 run artifacts + verify outputs + explicit reports。

## Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local contract refactor)`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Create single-purpose/single-flow/single-mode authoritative docs.
2) Reclassify overlapping overview/workflow docs and README source map.
3) Strengthen AGENTS role to operating rules + conflict stop path.
4) Strengthen task template and workflow gate for current-task truth fields.
5) Run check/contrast/fix loop:
   - `python scripts/workflow_checks.py`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
6) Run canonical verify gate: `scripts/verify_repo.ps1`.
7) Completion criteria: prove connected + accumulated + consumed.

## Notes / Decisions
- Default choices made: 保留历史文档但收敛为 lane/scope，不做破坏式删除。
- Alternatives considered: 直接删除旧 workflow/overview 文档；已拒绝（迁移风险过高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为流程契约重构，未触发新的用户可见失败条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository governance refactor rather than a reusable runtime workflow feature.

