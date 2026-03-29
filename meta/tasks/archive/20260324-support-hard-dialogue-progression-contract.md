# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-hard-dialogue-progression-contract.md`](archive/20260324-support-hard-dialogue-progression-contract.md)
- Date: 2026-03-24
- Topic: 客服/前台推进型对话硬约束合同化与可执行 lint
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-hard-dialogue-progression-contract`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户给出“对话与推进硬约束（强制执行）”，要求客服/前台/support agent 禁止机械重复并强制状态推进。
- Dependency check: `ADHOC-20260324-support-progress-truth-and-humanized-status` = `done`。
- Scope boundary: 只做对话合同、support 提示词、persona-lab 可执行 lint 与回归，不改 bridge/orchestrator 主流程。

## Task Truth Source (single source for current task)

- task_purpose: 将用户提出的硬约束沉淀为权威合同并转成可测试规则，避免仅停留在软文案要求。
- allowed_behavior_change:
  - `docs/11_task_progress_dialogue.md`
  - `docs/10_team_mode.md`
  - `docs/14_persona_test_lab.md`
  - `agents/prompts/support_lead_reply.md`
  - `scripts/ctcp_persona_lab.py`
  - `persona_lab/rubrics/response_style_lint.yaml`
  - `persona_lab/rubrics/task_progress_score.yaml`
  - `persona_lab/personas/production_assistant.md`
  - `persona_lab/cases/status_transition_reaction.yaml`
  - `tests/test_persona_lab_runner.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-hard-dialogue-progression-contract.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-hard-dialogue-progression-contract.md`
- forbidden_goal_shift: 不扩展到无关业务模块，不改运行态工程真源定义，不增加平行权威文档。
- in_scope_modules:
  - `docs/11_task_progress_dialogue.md`
  - `docs/10_team_mode.md`
  - `docs/14_persona_test_lab.md`
  - `agents/prompts/support_lead_reply.md`
  - `scripts/ctcp_persona_lab.py`
  - `persona_lab/rubrics/response_style_lint.yaml`
  - `persona_lab/rubrics/task_progress_score.yaml`
  - `persona_lab/personas/production_assistant.md`
  - `persona_lab/cases/status_transition_reaction.yaml`
  - `tests/test_persona_lab_runner.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-hard-dialogue-progression-contract.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-hard-dialogue-progression-contract.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `src/`
  - `include/`
- completion_evidence: 对话硬约束在合同、prompt、persona-lab lint 三层一致，回归测试与 canonical verify 可复现通过。

## Analysis / Find (before plan)

- Entrypoint analysis: 用户约束覆盖客服/前台/support 回复层，权威入口应是 `docs/11_task_progress_dialogue.md` 与 support prompt。
- Downstream consumer analysis: `scripts/ctcp_persona_lab.py` 与 `tests/test_persona_lab_runner.py` 是可执行 style-lint 消费层。
- Source of truth: `docs/11_task_progress_dialogue.md`（规则）+ `docs/10_team_mode.md`（lane 路由）+ persona-lab rubrics（可执行校验）。
- Current break point / missing wiring: 现有 lint 已覆盖“反机械”，但对“状态切换回应/低信息重复/负责人推进汇报”约束不够硬。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: support/frontdesk customer-visible reply generation (`support_lead_reply` + frontend render path)。
- current_module: dialogue contract + persona-lab lint engine + regression fixtures。
- downstream: support bot 对外回复质量、persona-lab 回归判定、quality gate 报告证据。
- source_of_truth: bound contract docs and persona-lab rubric execution。
- fallback: 若 verify 失败，记录 first failure point 与 minimal fix strategy。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_persona_lab_runner.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许只改 prompt 不改权威合同。
  - 不允许只改文档不补可执行 lint/测试。
  - 不允许跳过 canonical verify。
- user_visible_effect: 回复更稳定地包含状态判断与下一步，减少机械确认、重复催问和无增量汇报。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: task-progress contract explicitly codifies hard constraints for non-mechanical replies, anti-repetition, status-transition reaction, and final-delivery closure
- [x] DoD-2: support reply prompt and persona assets align with the same hard constraints without creating parallel authorities
- [x] DoD-3: persona-lab runner and regressions can fail on low-information/repetitive responses and pass on progression-oriented responses; canonical verify evidence is recorded

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local contract + persona scan)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 绑定任务并固定可改范围。
2) 先更新 `docs/11`，将用户硬约束转成权威规则条目。
3) 同步 `docs/10` 与 `support_lead_reply`，确保 lane 执行口径一致。
4) 扩展 persona-lab lint 与 case，覆盖状态切换回应、反重复、推进负责人口径。
5) 跑 focused tests + canonical verify，并记录 first failure / minimal fix。
6) 更新 `meta/reports/LAST.md` 与归档。

## Check / Contrast / Fix Loop Evidence

- check-1: 现有合同虽强调“非机械”，但未明确“状态变化后必须回应状态/原因/下一步负责人”。
- contrast-1: 用户要求必须在状态切换时给出一次短而可执行的状态说明。
- fix-1: 在 `docs/11` 增加状态切换响应硬规则与格式。
- check-2: 现有规则缺少“无新增信息默认少说”的去重约束。
- contrast-2: 用户要求无状态变化时低频保活且必须说明仍在执行哪一步。
- fix-2: 增加 anti-repeat 与 keepalive 规则，并在 persona-lab lint 落地。
- check-3: 当前 persona 测试可识别寒暄模板，但对“负责人推进汇报”语义检查不足。
- contrast-3: 用户要求“像团队负责人汇报：判断->动作->下一步/唯一决策”。
- fix-3: 扩展 lint 与 fixture，确保该结构可判定。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: 规则从 docs -> prompt -> persona-lab runner 连通。
  - accumulated: lint/rubric/case 对新约束有可积累的失败原因。
  - consumed: support/style 回归测试直接消费这些规则并给出 pass/fail 证据。

## Notes / Decisions

- Default choices made: 保持现有“单权威文档 + 可执行 lint”架构，不新增平行规则文件。
- Alternatives considered: 仅改提示词；不采纳（不可验证且不稳定）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 此次为合同强化而非新运行时故障，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded contract-hardening patch tied to current support lane semantics.
- persona_lab_impact: update required（rubric + case + runner + tests）。

## Results

- Files changed:
  - `docs/11_task_progress_dialogue.md`
  - `docs/10_team_mode.md`
  - `docs/14_persona_test_lab.md`
  - `agents/prompts/support_lead_reply.md`
  - `scripts/ctcp_persona_lab.py`
  - `persona_lab/rubrics/response_style_lint.yaml`
  - `persona_lab/rubrics/task_progress_score.yaml`
  - `persona_lab/personas/production_assistant.md`
  - `persona_lab/cases/status_transition_reaction.yaml`
  - `tests/test_persona_lab_runner.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-hard-dialogue-progression-contract.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-hard-dialogue-progression-contract.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_persona_lab_runner.py" -v` -> `0` (5 tests)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (45 tests)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | 客服/前台推进型对话硬约束合同化与可执行 lint | [→](archive/20260324-support-hard-dialogue-progression-contract.md) |
| 2026-03-24 | 客服进度真值修复与状态回复去机械化 | [→](archive/20260324-support-progress-truth-and-humanized-status.md) |
| 2026-03-24 | 客服主动通知控制器重构与状态推进拆分 | [→](archive/20260324-support-proactive-controller-refactor.md) |
| 2026-03-24 | librarian 后续角色统一 API 路由 | [→](archive/20260324-post-librarian-api-routing.md) |
| 2026-03-24 | 修复 triplet runtime wiring 基线失败链 | [→](archive/20260324-triplet-runtime-wiring-baseline-repair.md) |
| 2026-03-24 | API 连通性与项目内接线可用性验证 | [→](archive/20260324-api-connectivity-project-wiring-check.md) |
| 2026-03-24 | Support 发包动作只允许“测试通过 + 最终阶段”触发 | [→](archive/20260324-support-package-final-stage-gate.md) |
| 2026-03-24 | Support 单主流程状态机（禁用 Telegram 快速脚手架旁路） | [→](archive/20260324-support-single-mainline-state-machine.md) |
| 2026-03-24 | 支持对话模式二段判定（规则首判 + 模型仲裁） | [→](archive/20260324-support-mode-router-model-assist.md) |
| 2026-03-21 | src 功能边界拆分（Bridge 瘦身 + 单一文件操作适配层） | [→](archive/20260321-src-functional-boundary-refactor.md) |

Full archive: `meta/tasks/archive/`
