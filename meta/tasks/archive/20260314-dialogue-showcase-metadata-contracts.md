# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260314-dialogue-showcase-metadata-contracts.md`](20260314-dialogue-showcase-metadata-contracts.md)
- Date: 2026-03-14
- Topic: 任务推进型对话、测试展示链与版本真源合同重构
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260314-dialogue-showcase-metadata-contracts`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now?
  用户明确要求把项目从“会执行流程”推进到“会按固定主线推进任务、会生成测试用例、会展示测试过程、会避免机械式客服回复”的状态。当前仓库虽然已有 execution flow 和 support/test/scaffold 分散约束，但这些要求仍停留在软描述、历史报告或局部 lane 文档里，没有形成单一、可验收的合同。
- Dependency check:
  - `L0-CONTRACT-001`: `done`
- Scope boundary:
  - 只做 docs/meta/reports/backlog 范围内的合同重构与历史冲突标注。
  - 不改 `scripts/`、`frontend/`、`tools/`、`tests/` 等代码目录，不宣称当前 runtime 已新增截图自动化或 response-lint 自动执行器。
  - 不引入新的 agent 角色体系，不发散到完整桌面自动化实现。

## Task Truth Source (single source for current task)

- task_purpose:
  把“不要机械式回答”“测试要能自动生成并展示”“版本/报告/来源信息要同步”这些当前散落在 lane 文档、历史报告和用户口径里的要求，重写成可执行、可验收、可被后续 agent 直接消费的仓库级合同。
- allowed_behavior_change:
  - 可新增一份任务推进型对话合同文档，并更新 `docs/00_CORE.md`、`docs/01_north_star.md`、`docs/03_quality_gates.md`、`docs/04_execution_flow.md`、`docs/10_team_mode.md`、`docs/13_contracts_index.md`、`docs/25_project_plan.md`、`docs/30_artifact_contracts.md`、`docs/40_reference_project.md`、`docs/verify_contract.md`。
  - 可更新 `README.md` Doc Index、`ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 及对应 archive 文件记录证据。
- forbidden_goal_shift:
  - 不得把任务扩成 runtime 代码实现、截图引擎开发、verify 脚本开发或新增角色体系。
  - 不得只写审美建议或“更自然一点”式空话，必须落成合同、状态字段、禁用项、产物与验收项。
  - 不得直接删掉旧设计思路；如有冲突，必须标记 `deprecated` / `superseded`。
- in_scope_modules:
  - `docs/00_CORE.md`
  - `docs/01_north_star.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/11_task_progress_dialogue.md`
  - `docs/13_contracts_index.md`
  - `docs/25_project_plan.md`
  - `docs/30_artifact_contracts.md`
  - `docs/40_reference_project.md`
  - `docs/verify_contract.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260314-dialogue-showcase-metadata-contracts.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260314-dialogue-showcase-metadata-contracts.md`
- out_of_scope_modules:
  - `scripts/`
  - `frontend/`
  - `tools/`
  - `tests/`
  - `generated_projects/`
  - root `VERSION` value itself
  - 与本轮 docs contract 无关的其他未提交工作树改动
- completion_evidence:
  - 仓库内存在单一权威的任务推进型对话合同，明确机械式回答定义、阶段规则、禁用句式、状态绑定、自检和可测试 lint 项。
  - 核心合同、execution flow、quality gates、team mode、artifact contracts、reference project docs 已同步“测试设计 + 执行 + 展示”与 `VERSION` 单一真源规则。
  - 冲突旧文档被显式标记为 `deprecated` / `superseded`，而不是静默保留冲突口径。
  - workflow checks、contract checks、doc index、triplet guard、canonical verify 留下 `connected + accumulated + consumed` 证据或首个失败点。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户可见 task reply 的合同消费者是 support/frontend lane；当前仓库里的对应权威描述散落在 `docs/10_team_mode.md`、`docs/00_CORE.md`、历史 reports 和 backlog notes 中。
- Downstream consumer analysis:
  - 本轮合同会被后续 support/frontend 实现、report writers、verify reviewers、scaffold/reference export 路径和人工操作者消费，用来决定回复风格、测试展示产物和 provenance 口径。
- Source of truth:
  - 任务推进型对话：`docs/11_task_progress_dialogue.md`
  - Runtime contract：`docs/00_CORE.md`
  - Artifact/provenance contract：`docs/30_artifact_contracts.md`
  - Repo version：root `VERSION`
  - 当前任务与报告：`meta/tasks/CURRENT.md`、`meta/reports/LAST.md`
- Current break point / missing wiring:
  - “不要机械式回答”目前仍是审美要求，不是工程化合同。
  - 测试链文档仍偏向“运行已有脚本”，缺少 test-plan / test-cases / screenshot / demo-trace 的强约束。
  - provenance 里有 `source_commit` 但缺少统一 `source_version` 和 mismatch 规则。
  - 存在历史 verify 文档仍沿用旧 `proof.json` 口径，容易与当前主合同冲突。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream:
  user request -> repo contract readers -> future support/frontend/render/test/scaffold implementations
- current_module:
  `docs/11_task_progress_dialogue.md` + `docs/00_CORE.md` + `docs/03_quality_gates.md` + `docs/30_artifact_contracts.md` + `docs/40_reference_project.md` + task/report meta artifacts
- downstream:
  support lane docs and future runtime implementations, report writers, verify reviewers, scaffold/generated-project provenance consumers
- source_of_truth:
  `docs/11_task_progress_dialogue.md`, `docs/30_artifact_contracts.md`, root `VERSION`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`
- fallback:
  如果 runtime 目前还没有截图自动化或 dedicated lint，文档和报告必须显式记录“这是合同要求 / 下一阶段目标”，而不能假装能力已经接通
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/contract_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
- forbidden_bypass:
  - 只在 prompt、报告或 chat 里补口头规则，不改权威 docs
  - 只写“更自然”“更像真人客服”而不定义状态字段、禁用项、lint 与验收
  - 声称已具备截图展示 / metadata consistency 能力，却不给 artifact 结构和 fail-or-warn 规则
- user_visible_effect:
  - 后续 agent 面向用户的 task 回复会更像持续推进任务的执行人，而不是每轮重新接待；测试与交付结果也会有可展示、可解释、可追溯的合同基础。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: task-progress dialogue rules are authoritative, testable, and bound to execution state rather than style-only guidance
- [x] DoD-2: test capability contract covers test-plan generation, test-case generation, structured results, screenshots or snapshots, and user-visible demo trace artifacts
- [x] DoD-3: VERSION becomes the single repo version truth and scaffold or run provenance rules define fail vs warning on mismatch
- [x] DoD-4: quality-gate docs define response lint, test showcase acceptance, and metadata consistency acceptance for contract verification

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A (repo-local docs/meta scan only)`
- [x] Code changes allowed (`Docs-only, no code dirs touched`)
- [x] Patch applies cleanly (`git diff` generated; no destructive operations used)
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 绑定 `dialogue-showcase-metadata-contracts` task，并把当前用户要求写成 docs/meta 范围内的单主题合同重构。
2) 新增任务推进型对话合同，并同步 north star / core / execution flow / team mode 的权威链接与边界。
3) 扩展 artifact/reference/quality-gate 文档，把测试设计 + 执行 + 展示链，以及 `VERSION` 单一真源写成强约束。
4) 标注冲突旧文档为 `deprecated` / `superseded`，更新 problem registry、contracts index、queue、CURRENT/LAST。
5) 跑 local check / contrast / fix loop：
   - `python scripts/workflow_checks.py`
   - `python scripts/contract_checks.py`
   - `python scripts/sync_doc_links.py --check`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
   - 记录首个失败点与最小修复策略
6) Canonical verify gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
7) Completion criteria: prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made:
  - `VERSION` 作为 repo version 唯一权威来源，不新增第二个 repo-level version 文件。
  - `artifacts/test_cases.json` 兼任结构化测试结果真源；`test_summary.md` 与 `demo_trace.md` 是人类可读派生产物。
  - 截图不可用时，在 `artifacts/demo_trace.md` 中显式记录 `screenshots_not_available_reason`，而不是省略说明。
- Alternatives considered:
  - 直接把 `VERSION` 升到 `3.3.0`；拒绝，因为本轮是方向性合同收口，不是正式 release bump。
  - 新增更多 customer-facing / PM / demo 角色；拒绝，因为这会偏离现有主流程与用户约束。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision:
  - add two new recurring failure classes: task-turn mechanical restart drift and version/provenance inconsistency drift.
- Skill decision (`skillized: yes` or `skillized: no, because ...`):
  - skillized: no, because this is repository-level contract consolidation over existing lanes, not a reusable workflow asset by itself.

## Results

- Files changed:
  - `docs/00_CORE.md`
  - `docs/01_north_star.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/11_task_progress_dialogue.md`
  - `docs/13_contracts_index.md`
  - `docs/25_project_plan.md`
  - `docs/30_artifact_contracts.md`
  - `docs/40_reference_project.md`
  - `docs/verify_contract.md`
  - `README.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260314-dialogue-showcase-metadata-contracts.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260314-dialogue-showcase-metadata-contracts.md`
- Verification summary:
  - `python scripts/workflow_checks.py` => `0`
  - `python scripts/contract_checks.py` => `0`
  - `python scripts/sync_doc_links.py --check` => `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` => `0`
- Queue status update suggestion (`todo/doing/done/blocked`):
  - done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-14 | 任务推进型对话、测试展示链与版本真源合同重构 | [→](20260314-dialogue-showcase-metadata-contracts.md) |
| 2026-03-13 | support 项目包升级为 CTCP 风格 scaffold 交付，而不是单文件占位目录 | [→](20260313-support-ctcp-scaffold-package.md) |
| 2026-03-13 | support 回复锁到 api_agent，并把项目 zip/截图直发链路接到 Telegram | [→](20260313-support-api-first-local-degrade.md) |
| 2026-03-12 | support 到 production run 的渐进式链路测试 | [→](20260312-support-to-production-path-tests.md) |
| 2026-03-12 | support bot 项目记忆隔离、执行指令路由与 blocked 状态落地修复 | [→](20260312-support-project-state-grounding-hardening.md) |
| 2026-03-12 | support bot API 中文回复编码修复 | [→](20260312-support-api-encoding-hardening.md) |
| 2026-03-12 | support bot 全部用户可见回复走模型 | [→](20260312-support-all-turns-model-routing.md) |
| 2026-03-12 | support bot 记忆隔离与显式 API 路由锁定 | [→](20260312-support-memory-isolation-and-api-route-lock.md) |
| 2026-03-12 | support bot 接入 front bridge / shared whiteboard / librarian 后台流 | [→](20260312-support-bot-backend-bridge-wiring.md) |
| 2026-03-12 | 修复 support bot provider 连通性与兜底链路 | [→](20260312-support-provider-connectivity-repair.md) |

Full archive: `meta/tasks/archive/`
