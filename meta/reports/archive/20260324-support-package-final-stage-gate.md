# Demo Report - 20260324-support-package-final-stage-gate

## Topic

Support 发包动作只允许“测试通过 + 最终阶段”触发

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-support-package-final-stage-gate.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`

## Plan

1. Bind ADHOC queue item for package final-stage gate.
2. Add runtime gate that binds package delivery to `project_context.status` final+PASS truth.
3. Filter provider-requested and auto-synthesized package actions when gate is not open.
4. Enforce same gate at delivery execution layer to prevent bypass.
5. Update support contract doc and add focused regressions.
6. Run focused tests and canonical verify; record first failure point.

## Changes

- `scripts/ctcp_support_bot.py`
  - 新增/接线 `package_delivery_allowed` + `package_blocked_reason`。
  - `collect_public_delivery_state()` 现在要求“artifact ready + final+PASS gate”才置 `package_ready=true`。
  - `synthesize_delivery_actions()` 会删除不允许状态下的 `send_project_package`（含 provider 原始动作）。
  - `resolve_public_delivery_plan()` 对 `send_project_package` 再做执行层硬拦截。
  - `default_prompt_template()` 增加 `public_delivery.package_delivery_allowed` 约束说明。
  - t2p 自动注入包动作改为检查 `package_delivery_allowed`。
- `tests/test_support_bot_humanization.py`
  - 新增 `test_collect_public_delivery_state_blocks_package_until_final_pass`。
  - 新增 `test_build_final_reply_doc_filters_provider_package_action_when_gate_blocked`。
  - 更新发包正向用例输入，显式标注 `package_delivery_allowed=True`。
- `docs/10_team_mode.md`
  - 明确写死：`send_project_package` 仅可在 `verify_result=PASS` 且 `run_status` 最终态且无待决策时触发。
- `tests/test_runtime_wiring_contract.py`
  - 更新 Telegram 发包运行时契约用例，显式提供 final+PASS status context。
- `meta/backlog/execution_queue.json`
  - 将 `ADHOC-20260324-support-package-final-stage-gate` 状态更新为 `blocked` 并记录当前阻断原因。
- `meta/tasks/CURRENT.md`
  - 同步当前任务执行与验证证据。
- `meta/tasks/archive/20260324-support-package-final-stage-gate.md`
  - 与 `CURRENT.md` 同步归档快照。

## Verify

- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `1`
  - 说明：存在与本任务无关的既有失败（如 `call_support_lead` 未定义、`run_stdin_mode` StringIO `.buffer`、若干既有文案断言）。
- `$env:PYTHONPATH='tests'; python -m unittest -v test_support_bot_humanization.SupportBotHumanizationTests.test_collect_public_delivery_state_finds_generated_project_package_source test_support_bot_humanization.SupportBotHumanizationTests.test_collect_public_delivery_state_blocks_package_until_final_pass test_support_bot_humanization.SupportBotHumanizationTests.test_build_final_reply_doc_synthesizes_zip_action_and_rewrites_email_handoff test_support_bot_humanization.SupportBotHumanizationTests.test_build_final_reply_doc_filters_provider_package_action_when_gate_blocked test_support_bot_humanization.SupportBotHumanizationTests.test_emit_public_delivery_materializes_zip_and_sends_document` -> `0`
- `$env:PYTHONPATH='tests'; python -m unittest -v test_runtime_wiring_contract.RuntimeWiringContractTests.test_telegram_mode_emits_project_package_document_from_support_actions` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `1`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
  - first failure point: `triplet runtime wiring contract`（verify 已通过 workflow/plan/patch/contract/doc-index，停在 runtime wiring triplet）。
- minimal fix strategy:
  - 先在独立任务修复 `frontend/response_composer.py` 空提示词池导致的 `IndexError`；
  - 修复 `run_stdin_mode` 对 `StringIO` 无 `.buffer` 的兼容；
  - 处理 Telegram poll lock 文件清理失败，再重跑 canonical verify。

## Questions

- None.

## Demo

- 现在发包路径变为单一硬门禁：
  - 条件不满足（非最终态或 verify 非 PASS）时，provider 即便给出 `send_project_package` 也会被剔除。
  - 用户显式要求 zip 时，也不会自动补 `send_project_package`。
  - 即使动作列表中残留该动作，执行层仍会拒绝并记录阻断原因。
- 条件满足（final+PASS）时，原有 zip 发包流程保持可用。

## Integration Proof

- upstream: `process_message()` / `build_final_reply_doc()`
- current_module: `collect_public_delivery_state` + `synthesize_delivery_actions` + `resolve_public_delivery_plan`
- downstream: `emit_public_delivery()` Telegram document send
- source_of_truth: `project_context.status` (`run_status`, `verify_result`, `gate`, `needs_user_decision`)
- fallback: gate 不满足时仅保留状态/下一步文本，不触发发包
- forbidden_bypass:
  - 不允许 provider action 绕过
  - 不允许自动补 action 绕过
  - 不允许执行层绕过
