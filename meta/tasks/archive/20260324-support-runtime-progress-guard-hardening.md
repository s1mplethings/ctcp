# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-runtime-progress-guard-hardening.md`](archive/20260324-support-runtime-progress-guard-hardening.md)
- Date: 2026-03-24
- Topic: Support 运行时 task-progress 预发送硬校验加固
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-runtime-progress-guard-hardening`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 上一轮已完成合同与 lint 强化，但仍有“生产路径主要依赖启发式检测”的剩余风险；本轮将硬约束下沉到 runtime pre-send guard。
- Dependency check: `ADHOC-20260324-support-hard-dialogue-progression-contract` = `done`。
- Scope boundary: 仅加固 support runtime 回复守卫与对应回归，不改 bridge/orchestrator 主流程。

## Task Truth Source (single source for current task)

- task_purpose: 在 `build_final_reply_doc` 出口增加运行时硬校验，确保 task-like 回复满足“状态锚点 + 下一步 + 去机械低信息 + 真值完成声明”。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-runtime-progress-guard-hardening.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-runtime-progress-guard-hardening.md`
- forbidden_goal_shift: 不扩展到无关模块，不改 frontend bridge 契约，不引入第二事实源。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-runtime-progress-guard-hardening.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-runtime-progress-guard-hardening.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `scripts/ctcp_orchestrate.py`
  - `docs/00_CORE.md`
  - `src/`
  - `include/`
- completion_evidence: task-like 回复在 runtime 出口具备可执行守卫，针对低信息/重复/未绑定真值完成声明可自动纠偏，并通过 focused + canonical verify。

## Analysis / Find (before plan)

- Entrypoint analysis: `build_final_reply_doc` 是用户可见 `support_reply.json.reply_text` 的统一出口，适合放 pre-send guard。
- Downstream consumer analysis: Telegram/stin 模式都消费该出口，测试集中在 `test_support_bot_humanization.py` 与 `test_runtime_wiring_contract.py`。
- Source of truth: `build_progress_binding()` 提供结构化 phase/blocker/next_action 绑定数据。
- Current break point / missing wiring: 合同和 persona-lab 能识别问题，但 runtime 出口仍可能放行低信息或未对齐真值的回复。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: provider reply + frontend render output + progress_binding。
- current_module: support runtime pre-send guard。
- downstream: `support_reply.json.reply_text`、Telegram 用户可见消息。
- source_of_truth: bound run status/gate + progress binding。
- fallback: first failure + minimal fix。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不允许只改测试不改 runtime。
  - 不允许跳过 canonical verify。
  - 不允许弱化已有 support wiring 合同行为。
- user_visible_effect: 任务型回复更稳定地包含状态与下一步，重复/机械/超前完成声明在发送前被纠偏。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: support runtime applies pre-send guard for task-like replies: status anchor + next action + anti-low-info + anti-ungrounded-completion
- [x] DoD-2: same-state repeated replies are normalized into explicit no-change keepalive wording instead of duplicate text
- [x] DoD-3: focused regressions and canonical verify confirm runtime guard behavior without breaking existing support wiring contracts

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local support chain scan)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 在 runtime 回复出口添加 `task_progress_guard` 规则函数并接入 `build_final_reply_doc`。
2) 用 `progress_binding` 生成 grounded fallback，覆盖低信息、缺少状态锚点、缺少下一步、未绑定真值完成声明场景。
3) 增加同状态重复回复归一化（no-change keepalive）逻辑。
4) 补 focused regressions 并跑 canonical verify。
5) 更新报告与归档，关闭 queue item。

## Check / Contrast / Fix Loop Evidence

- check-1: persona-lab 可判失败，但 runtime 仍可能放行“我在处理/继续推进”低信息回复。
- contrast-1: task-like 回复应在发送前强制满足状态锚点+下一步。
- fix-1: 引入 runtime guard 与 grounded fallback 纠偏。
- check-2: 同状态下可能重复发同样文本。
- contrast-2: 应至少归一化为 no-change keepalive，避免重复语义消息。
- fix-2: 利用前一条回复 + progress digest 做重复检测与改写。
- check-3: 回复可能出现“已完成/可交付”超前声明。
- contrast-3: 完成声明必须绑定 final+PASS 真值。
- fix-3: 对未达 final ready 的完成声明做运行时拦截改写。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: pre-send guard 接入统一 reply 出口。
  - accumulated: guard 元信息记录触发原因与状态哈希。
  - consumed: focused tests 与 verify gate 直接消费并验证 guard 行为。

## Notes / Decisions

- Default choices made: 优先在 runtime 出口加硬校验，不再仅依赖测试侧 lint。
- Alternatives considered: 仅继续增强 persona-lab；不采纳（不能覆盖线上发送前最后一道关口）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: 该风险属于风格合同落地缺口，不新增 issue memory 案例，直接做运行时修复闭环。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded runtime hardening specific to current support reply path.
- persona_lab_impact: none（本轮聚焦 runtime guard）。

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-runtime-progress-guard-hardening.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-runtime-progress-guard-hardening.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (48 tests)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `0` (4 tests)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`): done

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | Support 运行时 task-progress 预发送硬校验加固 | [→](archive/20260324-support-runtime-progress-guard-hardening.md) |
| 2026-03-24 | 客服/前台推进型对话硬约束合同化与可执行 lint | [→](archive/20260324-support-hard-dialogue-progression-contract.md) |
| 2026-03-24 | 客服进度真值修复与状态回复去机械化 | [→](archive/20260324-support-progress-truth-and-humanized-status.md) |
| 2026-03-24 | 客服主动通知控制器重构与状态推进拆分 | [→](archive/20260324-support-proactive-controller-refactor.md) |
| 2026-03-24 | librarian 后续角色统一 API 路由 | [→](archive/20260324-post-librarian-api-routing.md) |
| 2026-03-24 | 修复 triplet runtime wiring 基线失败链 | [→](archive/20260324-triplet-runtime-wiring-baseline-repair.md) |
| 2026-03-24 | API 连通性与项目内接线可用性验证 | [→](archive/20260324-api-connectivity-project-wiring-check.md) |
| 2026-03-24 | Support 发包动作只允许“测试通过 + 最终阶段”触发 | [→](archive/20260324-support-package-final-stage-gate.md) |
| 2026-03-24 | Support 单主流程状态机（禁用 Telegram 快速脚手架旁路） | [→](archive/20260324-support-single-mainline-state-machine.md) |
| 2026-03-24 | 支持对话模式二段判定（规则首判 + 模型仲裁） | [→](archive/20260324-support-mode-router-model-assist.md) |

Full archive: `meta/tasks/archive/`
