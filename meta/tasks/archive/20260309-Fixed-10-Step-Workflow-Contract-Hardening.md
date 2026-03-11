# Update 2026-03-09 - Fixed 10-Step Workflow Contract Hardening

### Queue Binding
- Queue Item: `ADHOC-20260309-fixed-10-step-workflow`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 将仓库流程固化为强制 10-step 执行路径，补齐 analysis/find -> plan -> implement -> check/fix -> verify 节奏。
- Scope: `AGENTS.md` / `docs/00_CORE.md` / `ai_context/00_AI_CONTRACT.md` / `ai_context/CTCP_FAST_RULES.md` / `meta/templates/integration_check.md` / `meta/tasks/TEMPLATE.md` / `scripts/workflow_checks.py` / `scripts/verify_repo.ps1` / `scripts/verify_repo.sh` / `docs/03_quality_gates.md`。
- Out of scope: 产品业务逻辑与非流程型功能重构。

## Analysis / Find (before plan)
- Entrypoint analysis: 现有流程入口主要在 `AGENTS.md` 的执行顺序与 `scripts/workflow_checks.py` 的可执行门禁。
- Downstream consumer analysis: `scripts/verify_repo.ps1/.sh` 与 `scripts/plan_check.py` 是流程门禁最终消费端。
- Source of truth: `AGENTS.md`（流程）、`scripts/workflow_checks.py`（前置门禁）、`scripts/verify_repo.*`（最终验收门禁）。
- Current break point / missing wiring: 缺少强制 10-step 顺序、缺少 analysis/find 与 plan-before-implementation 的硬检查、缺少 pre-verify triplet guard gate。
- Repo-local search sufficient: `yes`
- External research artifact: `N/A`

## Integration Check (before implementation)
- upstream: `AGENTS.md` 执行顺序 + `scripts/workflow_checks.py`
- current_module: `scripts/workflow_checks.py`, `scripts/verify_repo.ps1`, `scripts/verify_repo.sh`
- downstream: `scripts/plan_check.py --executed-gates ... --check-evidence` 与 `meta/reports/LAST.md` 审计记录
- source_of_truth: `AGENTS.md` + `scripts/workflow_checks.py` + `scripts/verify_repo.*`
- fallback: 若 triplet guard 暂不适合集成 verify_repo，则保留在 step8 本地循环并在 `LAST.md` 明确 gap（本次已直接接入 verify_repo）
- acceptance_test: `python scripts/workflow_checks.py` + triplet 3 测 + `scripts/verify_repo.ps1`
- forbidden_bypass: 跳过 analysis/find、跳过 plan、跳过 check/fix loop、仅改 prompt 处理 wiring 问题
- user_visible_effect: 未来变更流程必须先分析与计划，再进入实现并循环修复；无法再“读文档后直接改代码然后一次 verify”。

## DoD Mapping (from request)
- [x] DoD-1: `AGENTS.md` 执行顺序重构为固定 10-step。
- [x] DoD-2: `docs/00_CORE.md` 增加固定 10-step 原则（简洁硬规则）。
- [x] DoD-3: `ai_context/00_AI_CONTRACT.md` 增补 10-step 与 connected/accumulated/consumed 完成证明。
- [x] DoD-4: `meta/templates/integration_check.md` 增补 `acceptance_test` 与 `user_visible_effect`。
- [x] DoD-5: `meta/tasks/TEMPLATE.md` 强化 analysis/find + integration check + fix loop + completion criteria。
- [x] DoD-6: `scripts/workflow_checks.py` 增加 10-step 关键证据字段门禁。
- [x] DoD-7: `scripts/verify_repo.ps1/.sh` 接入 triplet guard gate。
- [x] DoD-8: `docs/03_quality_gates.md` 与脚本门禁顺序同步。

## Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local workflow hardening)`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Analysis/find contract drift and gate coverage gaps.
2) Update contracts/docs/templates to fixed 10-step flow.
3) Implement executable gate checks in `scripts/workflow_checks.py`.
4) Add triplet guard gate to `scripts/verify_repo.ps1/.sh`.
5) Run local check / contrast / fix loop:
   - `python scripts/workflow_checks.py`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
6) Run canonical verify gate: `scripts/verify_repo.ps1`.
7) Completion criteria: prove connected + accumulated + consumed.

## Notes / Decisions
- Default choices made: 将 triplet guard 直接接入 verify_repo，作为 canonical gate 的硬子步骤。
- Alternatives considered: 仅在 AGENTS 文档声明 step8 不改 verify_repo；已拒绝（可跳过风险高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为流程固化改动，无新增用户可见失败缺陷条目；保持“若触发则必须记录”规则。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository workflow hardening, not a reusable runtime feature workflow.

