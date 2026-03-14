# Demo Report - LAST

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260314-persona-test-lab-contracts.md`](archive/20260314-persona-test-lab-contracts.md)
- Date: 2026-03-14
- Topic: Persona Test Lab 合同、隔离会话规则与回归资产落地

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `docs/11_task_progress_dialogue.md`
- `docs/10_team_mode.md`
- `docs/13_contracts_index.md`
- `docs/30_artifact_contracts.md`
- `docs/21_paths_and_locations.md`
- `docs/25_project_plan.md`
- `docs/verify_contract.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`

### Plan
1) 绑定 `persona-test-lab-contracts` task，并把独立人格测试需求收口成 docs/static-assets 范围内的单主题合同。
2) 新增 `docs/14_persona_test_lab.md`，定义三层分离、独立会话、评分与语言策略。
3) 新增 `persona_lab/` 静态资产：production persona、test user personas、rubrics、minimum regression cases。
4) 更新 core / flow / quality gates / team mode / paths / artifact contracts / verify doc，把 persona regression 接入现有主流程。
5) 跑 workflow/contract/doc-index/triplet/verify，记录首个失败点或通过证据。

### Changes
- `docs/14_persona_test_lab.md`
  - 新增 Persona Test Lab 单一权威文档，明确 production assistant、test user personas、judge/scoring 三层分离，fresh-session-per-case，English Contracts/Chinese Intent，评分标准和最小回归包。
- `persona_lab/README.md`, `persona_lab/personas/*.md`, `persona_lab/rubrics/*.yaml`, `persona_lab/cases/*.yaml`
  - 新增 repo-local 静态资产，定义 production persona、7 种 test user personas、3 份 rubrics、8 个最小回归 cases。
- `docs/00_CORE.md`, `docs/04_execution_flow.md`, `docs/10_team_mode.md`, `docs/11_task_progress_dialogue.md`
  - 把 persona regression 作为独立 supporting chain 接入 runtime truth、team lane 和 task-progress dialogue contract。
- `docs/03_quality_gates.md`, `docs/21_paths_and_locations.md`, `docs/30_artifact_contracts.md`
  - 定义 persona regression lint、repo 外 persona-lab run 路径、transcript/score/fail reasons/summary 产物与 anti-pollution 规则。
- `docs/01_north_star.md`, `docs/13_contracts_index.md`, `docs/25_project_plan.md`, `docs/verify_contract.md`
  - 把 Persona Test Lab 接入 repo purpose、contracts index、3.3.0 方向和 deprecated verify 注释。
- `artifacts/PLAN.md`
  - 把 `persona_lab/` 加入 `Scope-Allow`，使这轮静态资产改动与 patch gate 一致。
- `ai_context/problem_registry.md`, `meta/backlog/execution_queue.json`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`
  - 记录“风格回归测试与正式会话混用导致污染”的失败类，绑定新的 docs task，并留下 readlist/plan/verify/demo 证据。

### Verify
- `python scripts/sync_doc_links.py` => `0` (`no changes`)
- `python scripts/contract_checks.py` => `0`
- `python scripts/workflow_checks.py` => `1`
  - first failure point: `LAST.md missing mandatory workflow evidence: minimal fix strategy evidence`
  - minimal fix strategy: update `meta/reports/LAST.md` with explicit first-failure/minimal-fix lines, then rerun workflow checks before triplet guards and canonical verify
- `python scripts/workflow_checks.py` (rerun) => `0`
- `python scripts/sync_doc_links.py --check` => `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` => `1`
  - first failure point: `patch_check out-of-scope path (Scope-Allow): persona_lab/README.md`
  - minimal fix strategy: add `persona_lab/` to `artifacts/PLAN.md` `Scope-Allow`, then rerun canonical verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` (rerun) => `0`
  - final gate status: `PASS`
- final consistency recheck after report update => `workflow_checks=0`, `contract_checks=0`, `sync_doc_links --check=0`, `verify_repo(contract)=0`

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`
- Task archive: `meta/tasks/archive/20260314-persona-test-lab-contracts.md`
- Report archive: `meta/reports/archive/20260314-persona-test-lab-contracts.md`
- Authority doc: `docs/14_persona_test_lab.md`
- Static asset root: `persona_lab/README.md`
- External run root contract: `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/...`

### Integration Proof
- upstream: style-regression requirement -> contract readers -> future persona-lab runner/judge
- current_module: `docs/14_persona_test_lab.md` + `persona_lab/` + `docs/00_CORE.md` + `docs/30_artifact_contracts.md`
- downstream: future isolated persona sessions, judge outputs, support/style acceptance, audit reports
- source_of_truth: `docs/14_persona_test_lab.md`, `persona_lab/`, `docs/11_task_progress_dialogue.md`, `docs/21_paths_and_locations.md`, `docs/30_artifact_contracts.md`
- fallback: until a runner exists, the repo can claim contracts and static assets only, not automated persona execution
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/contract_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
- forbidden_bypass:
  - mixing persona tests into production support sessions
  - claiming style repair without transcript + score + fail reasons
  - writing persona-lab live outputs into repo
- user_visible_effect:
  - 后续可以用独立、可评分、可回归的方式验证“不要机械式回答”是否真的被修复，而不是继续在正式会话里试错。

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-14 | Persona Test Lab 合同、隔离会话规则与回归资产落地 | [→](archive/20260314-persona-test-lab-contracts.md) |
| 2026-03-14 | 任务推进型对话、测试展示链与版本真源合同重构 | [→](archive/20260314-dialogue-showcase-metadata-contracts.md) |
| 2026-03-13 | support 项目包升级为 CTCP 风格 scaffold 交付，而不是单文件占位目录 | [→](archive/20260313-support-ctcp-scaffold-package.md) |
| 2026-03-13 | support 回复锁到 api_agent，并把项目 zip/截图直发链路接到 Telegram | [→](archive/20260313-support-api-first-local-degrade.md) |
| 2026-03-12 | support 到 production run 的渐进式链路测试 | [→](archive/20260312-support-to-production-path-tests.md) |
| 2026-03-12 | support bot 项目记忆隔离、执行指令路由与 blocked 状态落地修复 | [→](archive/20260312-support-project-state-grounding-hardening.md) |
| 2026-03-12 | support bot API 中文回复编码修复 | [→](archive/20260312-support-api-encoding-hardening.md) |
| 2026-03-12 | support bot 全部用户可见回复走模型 | [→](archive/20260312-support-all-turns-model-routing.md) |
| 2026-03-12 | support bot 记忆隔离与显式 API 路由锁定 | [→](archive/20260312-support-memory-isolation-and-api-route-lock.md) |
| 2026-03-12 | support bot 接入 front bridge / shared whiteboard / librarian 后台流 | [→](archive/20260312-support-bot-backend-bridge-wiring.md) |

Full archive: `meta/reports/archive/`
