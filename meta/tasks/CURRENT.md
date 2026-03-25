# Task - support-delivery-quality-gate

## Queue Binding

- Queue Item: `ADHOC-20260325-support-delivery-quality-gate`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户反馈最终生成项目“细节不足、质量低”，需要在客服发包前加硬门禁，避免低质量结果被当成最终交付。
- Dependency check: `ADHOC-20260325-backend-test-default-output-and-support-trigger` = `done`
- Scope boundary: 仅改 support package delivery gate、对应测试和合同文档；不改 orchestrator 主流程与 backend create_job 业务逻辑。

## Task Truth Source (single source for current task)

- task_purpose: 为 support zip 交付增加可执行质量门禁，阻断低质量项目包。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `docs/10_team_mode.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift: 不修改 `scripts/ctcp_orchestrate.py` 状态机；不修改 `apps/project_backend/*` 生成编排；不引入新的外部依赖。
- in_scope_modules:
  - `scripts/`
  - `tests/`
  - `docs/`
- out_of_scope_modules:
  - `apps/`
  - `contracts/`
  - `shared/`
  - `frontend/`
- completion_evidence: 低质量目录在 final-pass 状态下也会被阻断发包；高质量目录可继续发送 zip。

## Analysis / Find (before plan)

- Entrypoint analysis: `collect_public_delivery_state` 目前只基于 `verify_result/run_status` + artifact 是否存在来决定 `package_delivery_allowed`。
- Downstream consumer analysis: `build_final_reply_doc` 和 `emit_public_delivery` 直接消费 `package_delivery_allowed/package_ready`，因此 gate 需要在 state 层完成。
- Source of truth: `scripts/ctcp_support_bot.py`、`tests/test_support_bot_humanization.py`、`tests/test_runtime_wiring_contract.py`。
- Current break point / missing wiring: 缺少“结构完整度 + 测试/展示证据”质量门禁，导致薄壳项目也可能触发发包。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `process_message` -> `collect_public_delivery_state`
- current_module: `scripts/ctcp_support_bot.py`
- downstream: `build_final_reply_doc` action filter + `emit_public_delivery`
- source_of_truth: delivery_state 中的 `package_delivery_allowed` 与新增 quality 字段
- fallback: 质量不足时保持状态说明/截图路径，不发送 package
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得删除既有 `verify_result=PASS` 最终态 gate
  - 不得绕过 `collect_public_delivery_state` 直接发包
  - 不得把低质量阻断改成仅提示不阻断
- user_visible_effect: 用户索要 zip 时，低质量项目会收到明确阻断说明；高质量项目可正常收到 zip。

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. 在 support delivery state 中增加 quality score/tier/ready/reason 计算与阈值常量。
2. 将 `package_delivery_allowed` 升级为“artifact + run final-pass + quality gate”联合判定。
3. 更新回归测试覆盖“低质量阻断、高质量放行、telegram 发包路径仍可发送”。
4. 更新 `docs/10_team_mode.md` 合同条款并记录 verify 证据。

## Check / Contrast / Fix Loop Evidence

- check-1: 当前 gate 只看 run 最终态，无法区分薄壳目录与高质量目录。
- contrast-1: 用户要求“更细节、更高质量”，低质量输出不应继续作为最终交付。
- fix-1: 在 `collect_public_delivery_state` 引入质量评分与阈值门禁，未达标直接阻断 `send_project_package`。

## Completion Criteria Evidence

- completion criteria: connected + accumulated + consumed
- connected: `collect_public_delivery_state` 产出质量字段并接入 delivery allow 判定。
- accumulated: 质量分、tier、reason 被写入 delivery_state 并进入 prompt context。
- consumed: `build_final_reply_doc/emit_public_delivery` 通过 `package_delivery_allowed` 消费门禁结果，低质量场景不再发包。

## Issue Memory Decision

- decision: 新增 issue memory（用户可见交付质量误报类问题）。
- rationale: 属于重复风险类缺陷，必须进入 failure memory。

## Skill Decision

- skillized: no, because 这是 support delivery runtime 的局部质量策略收敛，不是独立可复用 workflow。
