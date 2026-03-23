# Demo Report - Support Frontdesk State Machine

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `docs/11_task_progress_dialogue.md`
- `contracts/frontend_session_contract.md`
- `contracts/frontend_bridge_contract.md`
- `PATCH_README.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/LAST.md`
- `frontend/conversation_mode_router.py`
- `frontend/frontdesk_state_machine.py`
- `frontend/state_resolver.py`
- `frontend/response_composer.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_frontdesk_state_machine.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_frontend_rendering_boundary.py`
- `.agents/skills/ctcp-workflow/SKILL.md`

## Plan

1. Bind a new support frontdesk state-machine task and freeze scope.
2. Update authoritative support/session contracts to define explicit states, slots, interrupts, and boundaries.
3. Implement runtime state persistence and prompt/reply consumption on the existing support entrypoint.
4. Add focused regressions, run triplet guard evidence, then rerun canonical verify.

## Changes

- `ai_context/problem_registry.md`
- `contracts/frontend_session_contract.md`
- `docs/10_team_mode.md`
- `docs/13_contracts_index.md`
- `frontend/conversation_mode_router.py`
- `frontend/frontdesk_state_machine.py`
- `frontend/response_composer.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_frontdesk_state_machine.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260317-support-frontdesk-state-machine.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260317-support-frontdesk-state-machine.md`

## Verify

- `python -m py_compile frontend/frontdesk_state_machine.py frontend/conversation_mode_router.py frontend/response_composer.py scripts/ctcp_support_bot.py tests/test_frontdesk_state_machine.py tests/test_runtime_wiring_contract.py tests/test_support_bot_humanization.py` -> `0`
- `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point: `workflow gate (workflow checks)` because `meta/reports/LAST.md` was still missing explicit command evidence for `test_issue_memory_accumulation_contract.py` and `test_skill_consumption_contract.py`
- minimal fix strategy: record the triplet guard command evidence in `LAST.md`, refresh `meta/tasks/CURRENT.md` acceptance state, and rerun canonical verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- final canonical result: `OK`, including `workflow_gate`, `plan_check`, `patch_check`, `behavior_catalog_check`, `contract_checks`, `doc_index_check`, `triplet_guard`, `lite_replay`, and `python_unit_tests`
- lite replay run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260317-204958`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- final closure rerun: `OK` after queue/task/report closure sync
- final closure lite replay run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260317-205618`

## Questions

- None.

## Demo

- state-machine contract landed:
  - `contracts/frontend_session_contract.md` now defines the minimum state set, required slots, style profile, interrupt classes, persistence rules, and frontdesk behavior order
  - `docs/10_team_mode.md` now routes support reply generation through explicit frontdesk-state resolution before reply strategy
- runtime wiring landed:
  - `scripts/ctcp_support_bot.py` now persists `frontdesk_state` into `support_session_state.json`, injects it into prompt context, and records state/interrupt metadata in `latest_support_context`
  - `frontend/response_composer.py` now consumes `frontdesk_state` so `AwaitDecision` and status/result interruptions affect reply strategy instead of staying as inert metadata
  - `frontend/conversation_mode_router.py` no longer mistakes `状态机` for a `STATUS_QUERY`
- focused regression proof:
  - `test_style_change_updates_profile_and_preserves_resumable_execute`
  - `test_frontend_render_consumes_frontdesk_await_decision_state`
  - `test_support_bot_process_message_persists_frontdesk_state_snapshot`
  - `test_build_support_prompt_includes_frontdesk_state_and_style_profile`

## Integration Proof

- upstream: `scripts/ctcp_support_bot.py::process_message()`
- current_module: frontdesk-state derivation + support session persistence + prompt/reply consumption
- downstream: provider prompt context, frontend reply strategy, session continuity, proactive status push
- source_of_truth: support session contract + bound run artifacts; session memory remains non-authoritative
- fallback: if canonical verify fails, record only the first failing gate
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not land the state machine as prompt-only metadata
  - do not create a parallel workflow authority outside current docs/contracts
  - do not treat session slots as run truth
- user_visible_effect: support/frontdesk now keeps the main task line through interruptions, style changes, progress/result queries, and explicit decision gates instead of behaving like a latest-turn shell.
