# Demo Report - LAST

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260316-simlab-fixer-loop-repair.md`](archive/20260316-simlab-fixer-loop-repair.md)
- Date: 2026-03-16
- Topic: SimLab fixer-loop 回归修复（S15 / S16）

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_dispatch.py`
- `scripts/ctcp_orchestrate.py`
- `simlab/scenarios/S15_lite_fail_produces_bundle.yaml`
- `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`

### Plan

1) Bind a repair task scoped only to `S15` / `S16`.
2) Fix fixer request/prompt inputs so failed runs keep `failure_bundle.zip` visible.
3) Exempt managed pointer drift from the second-pass dirty-repo block without weakening real dirty protection.
4) Update issue memory for the recurring SimLab regression.
5) Re-run targeted SimLab scenarios and then canonical verify.
6) Record the new first failure point or full pass.

### Changes

- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-simlab-fixer-loop-repair.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-simlab-fixer-loop-repair.md`

### Verify

- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (baseline) -> `1`
- first failure point:
  - gate: `lite scenario replay`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-153942`
  - summary: `passed=12`, `failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: missing expected text `failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: missing expected text `"result": "PASS"`
- minimal fix strategy:
  - preserve `failure_bundle.zip` in fixer request missing-path inputs for blocked fixer patch paths
  - ignore managed `LAST_BUNDLE.txt` pointer drift when retrying a new fixer patch after a prior fail
- triplet command references:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

### Questions

- None.

### Demo

- baseline verify summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\summary.json`
- `S15` trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\S15_lite_fail_produces_bundle\TRACE.md`
- `S16` trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\S16_lite_fixer_loop_pass\TRACE.md`

### Integration Proof

- upstream: user requested direct repair of the current broken spots.
- current_module: `ctcp_dispatch` fixer request generation and `ctcp_orchestrate` fixer reapply dirty-repo guard.
- downstream: SimLab lite suite and canonical verify.
- source_of_truth: failing scenario traces, prompt artifacts, events, and current source files.
- fallback: if fixes still leave verify failing, record the new first failure only.
- acceptance_test:
  - `python simlab/run.py --scenario S15_lite_fail_produces_bundle`
  - `python simlab/run.py --scenario S16_lite_fixer_loop_pass`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not only edit scenario expectations
  - do not disable dirty-repo protection wholesale
  - do not patch unrelated Telegram/support behavior
- user_visible_effect: the repo should stop failing first at these two fixer-loop regressions.

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

Full archive: `meta/reports/archive/`
