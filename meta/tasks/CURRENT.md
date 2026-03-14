# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260314-persona-test-lab-contracts.md`](archive/20260314-persona-test-lab-contracts.md)
- Date: 2026-03-14
- Topic: Persona Test Lab 合同、隔离会话规则与回归资产落地
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260314-persona-test-lab-contracts`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now?
  用户要求新增一套独立人格测试工具 / Persona Test Lab，用来验证 production assistant 是否仍会出现机械式回答、接待台腔、重复寒暄、不推进任务、多语言退化和长对话污染等问题。当前仓库虽然已有 task-progress dialogue 合同，但还没有把 production persona、test user personas、judge scoring、fresh-session-per-case 和 transcript/score/fail reasons 产物固化成可回归的测试层。
- Dependency check:
  - `ADHOC-20260314-dialogue-showcase-metadata-contracts`: `done`
- Scope boundary:
  - 只做 docs/meta/backlog/report 与 repo-local static assets（`persona_lab/`）范围内的合同落地。
  - 不改 `scripts/`、`frontend/`、`tools/`、`tests/` 等代码目录，不宣称 runner/judge runtime 已经实现。
  - 不把人格测试混入正式 support 会话，不引入新的大角色体系。

## Task Truth Source (single source for current task)

- task_purpose:
  把“正式执行人格、测试人格和评分人格三层分离；每个测试用例独立开新会话；测试结果可评分、可回归、可证明”落成仓库级合同、静态资产与验收规则，而不是停留在口头建议。
- allowed_behavior_change:
  - 可新增 `docs/14_persona_test_lab.md` 与 `persona_lab/` 静态资产目录。
  - 可更新 `docs/00_CORE.md`、`docs/01_north_star.md`、`docs/03_quality_gates.md`、`docs/04_execution_flow.md`、`docs/10_team_mode.md`、`docs/11_task_progress_dialogue.md`、`docs/13_contracts_index.md`、`docs/21_paths_and_locations.md`、`docs/25_project_plan.md`、`docs/30_artifact_contracts.md`、`docs/verify_contract.md`。
  - 可在 scope gate 需要时更新 `artifacts/PLAN.md` 的 `Scope-Allow`，使本轮 docs/static-assets 变更与 patch gate 对齐。
  - 可更新 `README.md` Doc Index、`ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 及对应 archive 文件。
- forbidden_goal_shift:
  - 不得把任务扩成有趣人格扮演系统或新的 frontend 产品。
  - 不得把人格测试写进 production conversation state。
  - 不得只写“更自然一点”之类的审美建议，必须落成 persona、rubric、case、artifact、lint、pass/fail 规则。
- persona_lab_impact:
  `direct` (`docs/14_persona_test_lab.md`、`persona_lab/` 资产与外部 run artifact contract 同步新增)
- in_scope_modules:
  - `docs/00_CORE.md`
  - `docs/01_north_star.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/11_task_progress_dialogue.md`
  - `docs/13_contracts_index.md`
  - `docs/14_persona_test_lab.md`
  - `docs/21_paths_and_locations.md`
  - `docs/25_project_plan.md`
  - `docs/30_artifact_contracts.md`
  - `docs/verify_contract.md`
  - `artifacts/PLAN.md`
  - `persona_lab/README.md`
  - `persona_lab/personas/*.md`
  - `persona_lab/rubrics/*.yaml`
  - `persona_lab/cases/*.yaml`
  - `ai_context/problem_registry.md`
  - `README.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260314-persona-test-lab-contracts.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260314-persona-test-lab-contracts.md`
- out_of_scope_modules:
  - `scripts/`
  - `frontend/`
  - `tools/`
  - `tests/`
  - production `RUN.json` / `support_session_state.json`
  - repo-local live run outputs or screenshots
  - 与本轮 docs/static-assets 任务无关的其他未提交工作树改动
- completion_evidence:
  - 仓库存在单一权威的 Persona Test Lab 合同，明确三层分离、fresh-session-per-case、English Contracts/Chinese Intent、评分与 fail reasons 标准。
  - repo-local `persona_lab/` 静态资产存在 production persona、七种 test user personas、三份 rubrics、至少八个最小回归 case。
  - core/flow/gate/team/path/artifact 文档同步了 persona regression lint、repo 外 run 产物路径与 anti-pollution 规则。
  - workflow checks、contract checks、doc index、triplet guard、canonical verify 留下 `connected + accumulated + consumed` 证据。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - 这次改动的上游是用户对 production assistant 风格回归的要求；未来消费者是 persona-lab runner、judge/scoring layer、support/style 合同维护者。
- Downstream consumer analysis:
  - `docs/14_persona_test_lab.md` 与 `persona_lab/` 会被后续 runner/judge 实现、风格回归验收、support/frontend 风格维护和报告编写者消费。
- Source of truth:
  - style rule authority: `docs/11_task_progress_dialogue.md`
  - persona regression authority: `docs/14_persona_test_lab.md`
  - static asset authority: `persona_lab/`
  - external artifact authority: `docs/30_artifact_contracts.md` + `docs/21_paths_and_locations.md`
  - current task/report authority: `meta/tasks/CURRENT.md` + `meta/reports/LAST.md`
- Current break point / missing wiring:
  - production support 会话和风格测试容易混在同一上下文，导致测试污染。
  - 没有固定的 test user persona 集合、rubric、case baseline。
  - 缺少 transcript + score + fail reasons 的结构化 run 产物。
  - bilingual 与长对话漂移没有 isolated regression contract。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream:
  user request -> repo contract readers -> future persona-lab runner/judge -> style-regression maintainers
- current_module:
  `docs/14_persona_test_lab.md` + `persona_lab/` + `docs/00_CORE.md` + `docs/03_quality_gates.md` + `docs/04_execution_flow.md` + `docs/10_team_mode.md` + `docs/30_artifact_contracts.md`
- downstream:
  future isolated persona sessions, judge outputs, support/frontend style acceptance, run evidence reviewers
- source_of_truth:
  `docs/14_persona_test_lab.md`, `persona_lab/`, `docs/11_task_progress_dialogue.md`, `docs/30_artifact_contracts.md`, `docs/21_paths_and_locations.md`
- fallback:
  runtime runner/judge 尚未实现时，只能宣称合同与静态资产已落地；不得假装已经有自动化执行器
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/contract_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
- forbidden_bypass:
  - 在 production support 会话中顺手做风格测试，却不隔离新 session
  - 只靠主观描述“自然了很多”而没有 rubric 与 score
  - 把 persona-lab transcript / score / snapshots 写进 repo
- user_visible_effect:
  - 后续 agent 可以用独立、干净、可评分的方式证明“不要机械式回答”是否真的被修复，而不是只靠同一会话里的感觉判断。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: production assistant, test user personas, and judge scoring are contractually separated
- [x] DoD-2: every persona case requires a fresh session and writes standardized run artifacts outside the repo
- [x] DoD-3: repo-local persona definitions, rubrics, and minimum regression cases exist as auditable assets
- [x] DoD-4: quality gates and artifact contracts define persona regression acceptance and anti-pollution boundaries

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A (repo-local docs/meta scan only)`
- [x] Code changes allowed (`Docs-only plus repo-local static persona assets`)
- [x] Patch applies cleanly (`git diff` generated; no destructive operations used)
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 绑定 `persona-test-lab-contracts` task，把独立人格测试需求收口成 docs/static-assets 范围内的单主题改动。
2) 新增 `docs/14_persona_test_lab.md`，定义三层分离、独立会话、语言策略、评分/验收与最小回归包。
3) 新增 `persona_lab/` 静态资产：production persona、test user personas、rubrics、cases。
4) 更新 core / flow / gates / team mode / paths / artifact contracts，把 persona regression 接入主线，并明确 run outputs 只能在 repo 外。
5) 更新 problem registry、queue、CURRENT/LAST、archive，留下 `persona_lab_impact` 与 issue-memory 记录。
6) 跑 local check / contrast / fix loop：
   - `python scripts/workflow_checks.py`
   - `python scripts/contract_checks.py`
   - `python scripts/sync_doc_links.py --check`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
7) Canonical verify gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`

## Notes / Decisions

- Default choices made:
  - 使用 `docs/14_persona_test_lab.md` 作为单一权威文档，避免把 persona regression 规则散落到 support lane 或报告里。
  - `persona_lab/` 只保存静态资产；实际 transcripts/scores/fail reasons/snapshots 全部外置到 `CTCP_RUNS_ROOT`。
  - 语言策略采用 `English Contracts, Chinese Intent`，不新增并行中文术语体系。
- Alternatives considered:
  - 直接在 production support session 里加一个“风格测试模式”；拒绝，因为这会污染正式对话状态。
  - 把人格测试做成有趣角色系统；拒绝，因为目标是 regression 和 scoring，不是聊天娱乐。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision:
  - add one recurring failure class: style-regression context pollution without isolated persona lab.
- Skill decision (`skillized: yes` or `skillized: no, because ...`):
  - skillized: no, because this patch lands contracts and static assets only; runner/judge automation can be skillized later if runtime entrypoints become reusable.

## Results

- Files changed:
  - `docs/00_CORE.md`
  - `docs/01_north_star.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/11_task_progress_dialogue.md`
  - `docs/13_contracts_index.md`
  - `docs/14_persona_test_lab.md`
  - `docs/21_paths_and_locations.md`
  - `docs/25_project_plan.md`
  - `docs/30_artifact_contracts.md`
  - `docs/verify_contract.md`
  - `artifacts/PLAN.md`
  - `persona_lab/README.md`
  - `persona_lab/personas/*.md`
  - `persona_lab/rubrics/*.yaml`
  - `persona_lab/cases/*.yaml`
  - `README.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260314-persona-test-lab-contracts.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260314-persona-test-lab-contracts.md`
- Verification summary:
  - `python scripts/sync_doc_links.py` => `0` (`no changes`)
  - `python scripts/contract_checks.py` => `0`
  - `python scripts/workflow_checks.py` => `1` (`LAST.md missing mandatory workflow evidence: minimal fix strategy evidence`)
  - `python scripts/workflow_checks.py` (rerun after report fix) => `0`
  - `python scripts/sync_doc_links.py --check` => `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` => `1` (`patch_check out-of-scope path: persona_lab/README.md`)
  - minimal fix strategy: add `persona_lab/` to `artifacts/PLAN.md` `Scope-Allow`, then rerun canonical verify
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` (rerun) => `0`
  - final consistency recheck after report update: `workflow_checks=0`, `contract_checks=0`, `sync_doc_links --check=0`, `verify_repo(contract)=0`
- Queue status update suggestion (`todo/doing/done/blocked`):
  - done

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

Full archive: `meta/tasks/archive/`
