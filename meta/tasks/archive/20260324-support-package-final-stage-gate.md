# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-package-final-stage-gate.md`](archive/20260324-support-package-final-stage-gate.md)
- Date: 2026-03-24
- Topic: Support 发包动作只允许“测试通过 + 最终阶段”触发
- Status: `blocked`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-package-final-stage-gate`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户明确要求“未测试功能且未到最终阶段时，不允许直接发包”。
- Dependency check: `ADHOC-20260324-support-single-mainline-state-machine` = `blocked` (code landed, canonical verify blocked by unrelated `test_final.py`).
- Scope boundary: 仅修 support 包交付动作门禁与文档/回归；不改 orchestrator/bridge 主实现。

## Task Truth Source (single source for current task)

- task_purpose: 强制 `send_project_package` 只能在 bound run 已通过测试且处于最终可交付状态时触发。
- allowed_behavior_change: 可更新 `scripts/ctcp_support_bot.py`、`docs/10_team_mode.md`、`tests/test_support_bot_humanization.py`、`tests/test_runtime_wiring_contract.py`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260324-support-package-final-stage-gate.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260324-support-package-final-stage-gate.md`。
- forbidden_goal_shift: 不得恢复快通道；不得绕过主流程状态机；不得跳过 canonical verify。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-package-final-stage-gate.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-package-final-stage-gate.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `frontend/frontdesk_state_machine.py`
  - `src/`
  - `include/`
- completion_evidence: 未达 final+PASS 时，provider/自动动作里的 `send_project_package` 都被拦截；达到 final+PASS 才允许发包。

## Analysis / Find (before plan)

- Entrypoint analysis: `build_final_reply_doc()` 会消费 provider actions；`synthesize_delivery_actions()` 可自动补 `send_project_package`；`resolve_public_delivery_plan()` 负责实际 zip/document 发送。
- Downstream consumer analysis: 如果不在动作归一化与实际发送两层都设门禁，仍可能出现“文案或动作提前发包”。
- Source of truth: `project_context.status` (`run_status`, `verify_result`, `gate`, `needs_user_decision`) + `docs/10_team_mode.md`。
- Current break point / missing wiring: 包交付当前只看 `package_ready`，缺少“测试通过+最终阶段”硬条件。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `process_message()` -> `build_final_reply_doc()` -> `synthesize_delivery_actions()`。
- current_module: delivery action gate + public delivery plan gate。
- downstream: `emit_public_delivery()` 的 Telegram document/photo 发送。
- source_of_truth: `project_context.status` from `ctcp_front_bridge`。
- fallback: gate 未满足时仅保留状态回复/下一步，不发包。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得仅靠文案提示规避（必须 runtime gate）
  - 不得只拦自动动作而放行 provider 主动动作
  - 不得只拦动作列表而放行实际发送层
- user_visible_effect: 只有“测试通过且最终阶段”才会触发发包，其余阶段只汇报进度与下一步。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: send_project_package is blocked unless bound run status is final and verify_result is PASS
- [x] DoD-2: provider-requested and auto-synthesized package actions are both filtered out before public delivery when gate conditions are not met
- [x] DoD-3: support contract docs and focused regression tests explicitly cover the final-stage tested gate for package delivery

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local runtime/code scan only)
- [x] Code changes allowed (`Scoped package-delivery runtime gate`) 
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind queue item + task card.
2) Add package delivery gate helper bound to `project_context.status` final+PASS conditions.
3) Filter `send_project_package` in both action synthesis and delivery execution layers when gate unmet.
4) Keep screenshot delivery unaffected.
5) Update support contract wording to hard-require tested final stage before package delivery.
6) Add focused regression for package gate.
7) Run focused tests + canonical verify; record first failure + minimal fix.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: production log showed package action emitted immediately after project-create turn despite run gate still blocked.
  - contrast-1: expected behavior requires tested final-stage gate, but runtime only checked package artifact readiness.
  - fix-1: add strict status-based package gate and apply at action + delivery layers.
  - check-2: add focused regression and rerun verify.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: status gate from bridge flows into delivery gating.
  - accumulated: package gate decision persisted in delivery context for prompt/runtime consumption.
  - consumed: user-visible actions and actual Telegram delivery both obey the same gate.

## Notes / Decisions

- Default choices made: “不能发包”默认优先，只有 final+PASS 才放行。
- Alternatives considered: 仅在文案上改“稍后发包”；不采纳（仍可能实际发包）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: this is a user-visible premature-delivery class; keep tracked in issue memory.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a scoped runtime gate correction.
- persona_lab_impact: none.

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `docs/10_team_mode.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-package-final-stage-gate.md`
  - `meta/tasks/CURRENT.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `1`（存在与本任务无关的既有失败）
  - `$env:PYTHONPATH='tests'; python -m unittest -v test_support_bot_humanization.SupportBotHumanizationTests.test_collect_public_delivery_state_finds_generated_project_package_source test_support_bot_humanization.SupportBotHumanizationTests.test_collect_public_delivery_state_blocks_package_until_final_pass test_support_bot_humanization.SupportBotHumanizationTests.test_build_final_reply_doc_synthesizes_zip_action_and_rewrites_email_handoff test_support_bot_humanization.SupportBotHumanizationTests.test_build_final_reply_doc_filters_provider_package_action_when_gate_blocked test_support_bot_humanization.SupportBotHumanizationTests.test_emit_public_delivery_materializes_zip_and_sends_document` -> `0`
  - `$env:PYTHONPATH='tests'; python -m unittest -v test_runtime_wiring_contract.RuntimeWiringContractTests.test_telegram_mode_emits_project_package_document_from_support_actions` -> `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `1`（首个失败：`frontend/response_composer.py` 既有 `IndexError`，并伴随 `run_stdin_mode` 与锁文件清理既有问题）
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`（当前首失败：`triplet runtime wiring contract`）
  - minimal fix strategy: 先在独立任务修复 `frontend/response_composer.py` 的空提示词池索引与 `run_stdin_mode` StringIO 兼容，再处理 Telegram lock 清理，再重跑 canonical verify。
- Queue status update suggestion (`todo/doing/done/blocked`): blocked

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | Support 发包动作只允许“测试通过 + 最终阶段”触发 | [→](archive/20260324-support-package-final-stage-gate.md) |
| 2026-03-24 | Support 单主流程状态机（禁用 Telegram 快速脚手架旁路） | [→](archive/20260324-support-single-mainline-state-machine.md) |
| 2026-03-24 | 支持对话模式二段判定（规则首判 + 模型仲裁） | [→](archive/20260324-support-mode-router-model-assist.md) |
| 2026-03-21 | src 功能边界拆分（Bridge 瘦身 + 单一文件操作适配层） | [→](archive/20260321-src-functional-boundary-refactor.md) |
| 2026-03-17 | Support frontdesk 显式状态机与任务槽位接线 | [→](archive/20260317-support-frontdesk-state-machine.md) |
| 2026-03-17 | Support 旧项目进度追问绑定真实 run 状态 | [→](archive/20260317-support-previous-project-status-grounding.md) |
| 2026-03-17 | Support greeting turn 保留主动进度基线 | [→](archive/20260317-support-proactive-baseline-preserve-on-greeting.md) |
| 2026-03-17 | Support 主动推送误复用寒暄修复 | [→](archive/20260317-support-proactive-push-greeting-dup-guard.md) |
| 2026-03-16 | Support 主动进度推送与旧大纲恢复 | [→](archive/20260316-support-proactive-progress-and-resume.md) |
| 2026-03-16 | Support 状态/进度回复绑定真实 run 进展 | [→](archive/20260316-support-status-progress-grounding.md) |

Full archive: `meta/tasks/archive/`
