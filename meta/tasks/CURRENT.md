# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260316-simlab-fixer-loop-repair.md`](archive/20260316-simlab-fixer-loop-repair.md)
- Date: 2026-03-16
- Topic: SimLab fixer-loop 回归修复（S15 / S16）
- Status: `doing`

## Queue Binding

- Queue Item: `ADHOC-20260316-simlab-fixer-loop-repair`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户要求直接解决当前真实失败点，而 canonical verify 稳定卡在 `S15` / `S16`。
- Dependency check: `ADHOC-20260316-telegram-to-project-generation-smoke` = `done`.
- Scope boundary: 允许修改 `scripts/ctcp_dispatch.py`、`scripts/ctcp_orchestrate.py`、`tests/fixtures/patches/` 下本次回归对应 fixture、`ai_context/problem_registry.md` 与 queue/current/report meta 文件；不扩到 Telegram/support/scaffold 其他功能。

## Task Truth Source (single source for current task)

- task_purpose: 修复 canonical verify 当前首个失败点对应的两个 SimLab 回归：先保住 `S15` 的 fixer prompt `failure_bundle.zip` 输入与 `S16` 的 managed dirty reapply，再修复因 README 头部漂移导致 `S15/S16` fixture patch 不再进入预期 verify/fixer-loop 分支的问题。
- allowed_behavior_change: 可更新 `scripts/ctcp_dispatch.py`、`scripts/ctcp_orchestrate.py`、`tests/fixtures/patches/lite_fail_bad_readme_link.patch`、`tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`、`ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260316-simlab-fixer-loop-repair.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260316-simlab-fixer-loop-repair.md`。
- forbidden_goal_shift: 不得顺手重构 dispatcher/orchestrator 其他路径；不得扩修 Telegram/support/scaffold 逻辑；不得只改 SimLab 场景断言绕开真实运行时缺陷。
- in_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `tests/fixtures/patches/lite_fail_bad_readme_link.patch`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260316-simlab-fixer-loop-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260316-simlab-fixer-loop-repair.md`
- out_of_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `tools/providers/`
  - `frontend/`
  - `docs/`
- completion_evidence: `S15` 场景里的 fixer prompt 明确包含 `failure_bundle.zip` 且场景重新进入 verify 失败分支，`S16` 第二次 advance 后 `verify_report.json` 为 `PASS`，issue memory 记录该回归及修复状态，canonical verify 已执行并记录最终结果。

## Analysis / Find (before plan)

- Entrypoint analysis: 当前失败入口都是 `scripts/ctcp_orchestrate.py advance` 驱动出的 fixer-loop 路径；`S15` 经过 `ctcp_dispatch` 生成 fixer prompt，`S16` 经过 `repo_dirty_status()` 进入 reapply 前脏仓库保护。
- Downstream consumer analysis: canonical verify、SimLab lite suite、以及之后任何失败后进入 fixer-loop 的运行路径都会消费这两个修复。
- Source of truth: `scripts/ctcp_dispatch.py` 的 request/prompt 输入、`scripts/ctcp_orchestrate.py` 的 `ready_apply` / `ready_verify` 状态推进、`simlab/scenarios/S15_lite_fail_produces_bundle.yaml`、`simlab/scenarios/S16_lite_fixer_loop_pass.yaml`、`scripts/verify_repo.ps1`。
- Current break point / missing wiring: 第一轮 runtime 修复后，provider prompt 丢 bundle 与 managed pointer dirty block 已被推进；最新首个失败点变成 `tests/fixtures/patches/lite_fail_bad_readme_link.patch` / `lite_fix_remove_bad_readme_link.patch` 仍引用旧 README 头部，导致 `S15/S16` 在 patch-first gate 就失败，无法进入预期 verify/fixer-loop 分支。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: 用户要求直接解决当前真实失败点，而不是停留在 smoke 结论。
- current_module: `ctcp_dispatch` 的 fixer request 构造 + `ctcp_orchestrate` 的 patch reapply 脏仓库保护。
- downstream: SimLab lite suite、canonical verify、失败后的 failure-bundle/fixer loop。
- source_of_truth: `S15` / `S16` 场景输出的 run_dir 证据 + orchestrator/dispatch 源码。
- fallback: 若最小修复后 canonical verify 仍失败，则记录新的首个失败点并停止在该点。
- acceptance_test:
  - `python simlab/run.py --scenario S15_lite_fail_produces_bundle`
  - `python simlab/run.py --scenario S16_lite_fixer_loop_pass`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得只改 SimLab 场景断言
  - 不得通过完全关闭 dirty-repo 保护来放过所有脏状态
  - 不得通过放宽 `git apply --check` 或关闭 patch-first gate 来掩盖 fixture 漂移
  - 不得只改 fallback prompt，而不修 provider 实际生成的 fixer request 输入
- user_visible_effect: 当前仓库默认验收不应再先死在 `S15/S16` 这两个 fixer-loop 回归上。

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: fixer dispatch prompt for failed or rejected patch paths preserves `failure_bundle.zip`
- [ ] DoD-2: managed runtime pointer drift no longer blocks fixer reapply in S16 while preserving real dirty-repo protection
- [ ] DoD-3: S15/S16 对应的 README fixture patch 重新命中当前仓库头部并恢复原场景意图
- [ ] DoD-4: issue memory records the recurring S15/S16 regression and repaired status
- [ ] DoD-5: the canonical verify_repo entrypoint is executed and its current result is recorded

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local docs/runtime scan only)
- [x] Code changes allowed (`Scoped code fix in orchestrator/dispatch + issue memory + meta only`)
- [x] Patch applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind a repair task scoped only to `S15` / `S16`.
2) Fix fixer request/prompt inputs so failed runs keep `failure_bundle.zip` visible.
3) Exempt managed pointer drift from the second-pass dirty-repo block without weakening real dirty protection.
4) Refresh the stale README-based SimLab fixture patches so `S15/S16` re-enter their intended verify/fixer-loop branches.
5) Update issue memory for the recurring SimLab regression.
6) Re-run targeted SimLab scenarios, lite suite, and then canonical verify.
7) Record the new first failure point or full pass.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (baseline) -> `1`
  - baseline first failure gate: `lite scenario replay`
  - baseline summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-153942/summary.json`
  - baseline `S15` symptom: fixer prompt missing `failure_bundle.zip`
  - baseline `S16` symptom: `APPLY_BLOCKED_DIRTY` with `dirty_preview=M meta/run_pointers/LAST_BUNDLE.txt`
  - post-runtime-fix current symptom: `S15/S16` fixture patches no longer apply because current README header drifted from the fixture context

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `ctcp_dispatch` 的 fixer request 和 `ctcp_orchestrate` 的 ready_apply/ready_verify 路径直接连接到 `S15` / `S16` 失败证据。
  - accumulated: 最新失败 run_dir、TRACE、events、prompt、verify_report 都已收集。
  - consumed: 目标修复要由 SimLab 场景和 canonical verify 实际消费，而不是停留在代码阅读结论。

## Notes / Decisions

- Default choices made: 保持修复只落在 orchestrator/dispatch/fixture/issue-memory，不碰 Telegram/support 已跑通的路径。
- Alternatives considered: 直接改 SimLab 断言接受当前 prompt 内容；暂不采纳，先按运行时合同修真实缺口。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: required; this is a recurring integration failure and will be更新 in `ai_context/problem_registry.md`.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: yes; this task uses `ctcp-workflow`, `ctcp-verify`, and `ctcp-failure-bundle`.
- persona_lab_impact: none; this task does not change customer-facing reply contracts.

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260316-simlab-fixer-loop-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260316-simlab-fixer-loop-repair.md`
- Verification summary:
  - baseline canonical repo verify:
    - final run: `1` (`lite scenario replay`; `passed=12`, `failed=2`)
    - failed scenarios:
      - `S15_lite_fail_produces_bundle`: missing expected text `failure_bundle.zip`
      - `S16_lite_fixer_loop_pass`: missing expected text `"result": "PASS"`
- Queue status update suggestion (`todo/doing/done/blocked`): doing.

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-16 | SimLab fixer-loop 回归修复（S15 / S16） | [→](archive/20260316-simlab-fixer-loop-repair.md) |
| 2026-03-16 | Telegram 测试到项目生成 smoke 联通与启动检查 | [→](archive/20260316-telegram-to-project-generation-smoke.md) |
| 2026-03-16 | Markdown 流程拆清与逐条表达 | [→](archive/20260316-markdown-flow-clarity.md) |
| 2026-03-16 | 全项目健康检查与阻塞问题审计 | [→](archive/20260316-repo-health-audit.md) |
| 2026-03-15 | 完整默认验收流回归验证 | [→](archive/20260315-full-flow-validation.md) |
| 2026-03-15 | 薄主合同 + 单流程 + 局部覆盖的 agent 规则收口 | [→](archive/20260315-agent-contract-thin-mainline.md) |
| 2026-03-15 | Persona Test Lab fixture runner / judge 基线落地 | [→](archive/20260315-persona-test-lab-runner-judge.md) |
| 2026-03-14 | Persona Test Lab 合同、隔离会话规则与回归资产落地 | [→](archive/20260314-persona-test-lab-contracts.md) |
| 2026-03-14 | 任务推进型对话、测试展示链与版本真源合同重构 | [→](archive/20260314-dialogue-showcase-metadata-contracts.md) |
| 2026-03-13 | support 项目包升级为 CTCP 风格 scaffold 交付，而不是单文件占位目录 | [→](archive/20260313-support-ctcp-scaffold-package.md) |

Full archive: `meta/tasks/archive/`
