# Report - support-proactive-controller-refactor

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/04_execution_flow.md`
- `docs/10_team_mode.md`
- `docs/11_task_progress_dialogue.md`
- `docs/architecture/contracts/frontend_session_contract.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_front_api.py`
- `frontend/frontdesk_state_machine.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_frontdesk_state_machine.py`

## Plan

1. Bind new ADHOC queue item and update current task card.
2. Add standalone support controller for proactive state/notify decisions.
3. Extend session state with controller + dedupe + outbound queue fields.
4. Wire proactive Telegram cycle to consume controller outbound jobs.
5. Add focused regressions for decision dedupe/cooldown and result gate.
6. Run focused tests and canonical verify.

## Changes

- `scripts/ctcp_support_controller.py` (new)
- `scripts/ctcp_support_bot.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `docs/10_team_mode.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-support-proactive-controller-refactor.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260324-support-proactive-controller-refactor.md`

## Verify

- `python scripts/workflow_checks.py` -> `0`
- `python -m py_compile scripts/ctcp_support_controller.py scripts/ctcp_support_bot.py tests/test_runtime_wiring_contract.py tests/test_support_bot_humanization.py` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (43 tests)
- `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> `0` (6 tests)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point: none (final gate pass)
- minimal fix strategy: not needed after final gate pass

## Questions

- None.

## Demo

- 新增后台控制器 `ctcp_support_controller.py`，输出显式状态与 outbound jobs（`progress|decision|result|error`）。
- support bot proactive cycle 改为“先 controller 决策，再 Telegram 发送”，并写回 dedupe/cooldown 状态。
- 决策类主动提问按 prompt hash 去重；执行中无变化默认静默，仅低频 keepalive；结果通知仅在 final+PASS 且无待决策时触发。

## Integration Proof

- upstream: `run_telegram_mode` idle polling -> `run_proactive_support_cycle`
- current_module: `ctcp_support_controller.decide_and_queue/pop_outbound_jobs/mark_job_sent`
- downstream: `emit_public_message` + session `notification_state/controller_state/outbound_queue` persistence
- source_of_truth: `ctcp_front_bridge.ctcp_get_support_context` status/gate/decisions
- fallback: controller remains rule-based and does not synthesize run completion outside bridge truth
- acceptance_test:
  - proactive decision one-shot + cooldown regression
  - result gate regression (not-final PASS is not result)
  - canonical verify pass

