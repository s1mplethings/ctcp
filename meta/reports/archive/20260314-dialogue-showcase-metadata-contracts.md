# Demo Report - LAST

## Latest Report

- File: [`meta/reports/archive/20260314-dialogue-showcase-metadata-contracts.md`](20260314-dialogue-showcase-metadata-contracts.md)
- Date: 2026-03-14
- Topic: 任务推进型对话、测试展示链与版本真源合同重构

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/10_team_mode.md`
- `docs/30_artifact_contracts.md`
- `docs/13_contracts_index.md`
- `docs/25_project_plan.md`
- `docs/40_reference_project.md`
- `docs/05_agent_mode_matrix.md`
- `docs/verify_contract.md`
- `docs/00_overview.md`
- `docs/17_interactions.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `meta/tasks/TEMPLATE.md`
- `scripts/verify_repo.ps1`
- `scripts/workflow_checks.py`

### Plan
1) 绑定 `dialogue-showcase-metadata-contracts` task，并把当前用户要求写成 docs/meta 范围内的单主题合同重构。
2) 新增任务推进型对话合同，把“不要机械式回答”改写为状态绑定、阶段规则、禁用句式、自检和 response lint。
3) 更新 core / execution flow / quality gates / team mode / artifact contracts / reference-project docs，把“测试设计 + 执行 + 展示”和 `VERSION` 单一真源写成硬规则。
4) 标记冲突旧文档为 `deprecated` / `superseded`，并同步 problem registry、contracts index、queue、CURRENT/LAST、archive。
5) 跑 local checks、triplet guard 和 canonical verify（`contract` profile），记录首个失败点与最小修复策略。

### Changes
- `docs/11_task_progress_dialogue.md`
  - 新增单一权威的任务推进型对话合同，定义机械式回答、目标风格、阶段规则、状态绑定、禁用句式、自检与 response lint。
- `docs/00_CORE.md`, `docs/01_north_star.md`, `docs/04_execution_flow.md`, `docs/10_team_mode.md`
  - 把 task-progress dialogue、展示链、`VERSION` provenance 和 user-visible grounding 接入 repo purpose / runtime truth / flow / support lane。
- `docs/03_quality_gates.md`, `docs/30_artifact_contracts.md`, `docs/40_reference_project.md`
  - 定义 test plan / cases / summary / screenshots / demo trace 产物与 lint 验收，并把 `source_version + source_commit` 写成 provenance contract。
- `docs/25_project_plan.md`, `docs/13_contracts_index.md`, `docs/verify_contract.md`
  - 增加 3.3.0 方向说明、合同索引入口，并把旧 verify 文档显式标记为 `deprecated`。
- `ai_context/problem_registry.md`, `meta/backlog/execution_queue.json`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`
  - 记录新的重复失败类、绑定当前合同重构任务，并留下 readlist/plan/verify/demo 证据。

### Verify
- `python scripts/workflow_checks.py` => `0`
- `python scripts/contract_checks.py` => `0`
- `python scripts/sync_doc_links.py --check` => `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` => `0`
  - note: canonical verify skipped triplet/lite/unit gates inside the `contract` profile, but the three triplet guard tests were also run manually in this task and passed.
- first failure point: none (`workflow_checks`, `contract_checks`, `doc index`, triplet guards, and canonical verify all passed)
- minimal fix strategy: none required

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`
- Task archive: `meta/tasks/archive/20260314-dialogue-showcase-metadata-contracts.md`
- Report archive: `meta/reports/archive/20260314-dialogue-showcase-metadata-contracts.md`
- New contract entry: `docs/11_task_progress_dialogue.md`
- Version authority: root `VERSION`

### Integration Proof
- upstream: support/frontend-visible task reply path, run/test report writers, scaffold/live-reference provenance writers
- current_module: `docs/11_task_progress_dialogue.md` + `docs/00_CORE.md` + `docs/03_quality_gates.md` + `docs/30_artifact_contracts.md` + `docs/40_reference_project.md`
- downstream: `docs/10_team_mode.md`, quality-gate review, report writers, generated project metadata, future response/showcase implementations
- source_of_truth: `docs/11_task_progress_dialogue.md`, `docs/30_artifact_contracts.md`, root `VERSION`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`
- fallback: if runtime has not yet implemented screenshot capture or automated lint, the docs/report must say so explicitly and cannot claim the capability is already wired
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/contract_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
- forbidden_bypass:
  - leaving the new rules only in prompts, reports, or chat output
  - claiming `source_version` truth without binding it to root `VERSION`
  - claiming tests were generated/shown without the required artifact pack
- user_visible_effect:
  - 后续 agent 可以更稳定地沿固定主线推进任务、展示测试过程并解释结果，而不是退回接待式话术。
