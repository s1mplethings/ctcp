# Task - support-frontdesk-state-machine

## Queue Binding

- Queue Item: `ADHOC-20260317-support-frontdesk-state-machine`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户这轮明确要求把 support/frontdesk 从“按最后一句自由回复”收紧为状态机驱动的任务型前台，而且要求状态、槽位、决策门和中断恢复都落成结构。
- Dependency check: `ADHOC-20260317-support-previous-project-status-grounding` = `done`
- Scope boundary: 只落 support/frontend 前台状态机与其持久槽位接线；不改 CTCP 后台主执行流，也不新增平行 workflow authority。

## Task Truth Source (single source for current task)

- task_purpose: 让 support 前台在现有 `conversation_mode -> bridge -> render` 主链上增加显式 frontdesk state machine，持久化主线任务槽位、风格槽位和中断恢复信息，并让回复策略消费这份结构。
- allowed_behavior_change: 可更新 `contracts/frontend_session_contract.md`、`docs/10_team_mode.md`、`docs/13_contracts_index.md`、`frontend/conversation_mode_router.py`、`frontend/frontdesk_state_machine.py`、`frontend/response_composer.py`、`scripts/ctcp_support_bot.py`、`tests/test_frontdesk_state_machine.py`、`tests/test_runtime_wiring_contract.py`、`tests/test_support_bot_humanization.py`、`ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260317-support-frontdesk-state-machine.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260317-support-frontdesk-state-machine.md`。
- forbidden_goal_shift: 不得新增第二套平行 prompt/workflow authority；不得只改 prompt 文案而不落状态结构；不得绕开 `scripts/ctcp_front_bridge.py`；不得把 support state 伪装成工程真源。
- in_scope_modules:
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
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260317-support-frontdesk-state-machine.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260317-support-frontdesk-state-machine.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_orchestrate.py`
  - `tools/providers/`
  - `persona_lab/`
- completion_evidence: support runtime/session artifacts 持久化 frontdesk state 和槽位；prompt/render 路径消费这份结构；focused regressions 覆盖状态 derivation、style persistence、interrupt recovery / decision gating；canonical verify 已执行并记录结果。

## Analysis / Find (before plan)

- Entrypoint analysis: 当前入口仍是 `scripts/ctcp_support_bot.py::process_message()`，它先算 `conversation_mode`、再做 bridge sync、再构造 prompt 和 reply，但缺少统一的 frontdesk state object。
- Downstream consumer analysis: 当前 downstream 主要是 `build_support_prompt()`、`build_final_reply_doc()` 和 `frontend/response_composer.py`；它们各自消费局部字段，没有共享的状态机快照。
- Source of truth: `contracts/frontend_session_contract.md`、`docs/10_team_mode.md`、`frontend/conversation_mode_router.py`、`frontend/response_composer.py`、`scripts/ctcp_support_bot.py`、`tests/test_runtime_wiring_contract.py`、`tests/test_support_bot_humanization.py`。
- Current break point / missing wiring: support session 虽有 memory zones 与 `conversation_mode`，但没有显式 state / slots / interrupt / resumable_state，所以任务主线、风格调整和中断恢复只能散落在条件分支里。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `scripts/ctcp_support_bot.py::process_message()` 的 support entrypoint。
- current_module: support session state + prompt context + frontend reply pipeline。
- downstream: provider prompt、frontend reply strategy、support session persistence、后续 proactive/status/decision path。
- source_of_truth: support session state contract 与 bound run artifacts；chat memory 仅作非权威上下文。
- fallback: 若 canonical verify 失败，只记录首个失败 gate 和最小修复路径。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得把 frontdesk state machine 只写进文档或 prompt，不接 runtime/session
  - 不得引入与 `conversation_mode`、`visible_state` 脱节的第三套自由状态
  - 不得把 session cache 当作 run truth
- user_visible_effect: support/frontdesk 应在插话、风格调整、进度追问、结果返回和关键决策时保持主线不断线。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: authoritative support/session contracts define an explicit frontdesk state machine, required slots, interrupt classes, and the boundary that it augments rather than replaces the existing CTCP flow
- [x] DoD-2: support runtime persists and consumes frontdesk state plus style profile so reply strategy, decision gating, and interrupt recovery follow explicit state instead of only the latest-turn free reply path
- [x] DoD-3: focused regressions plus canonical verify prove the support entrypoint accumulates and consumes the new state-machine structure

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local only)
- [x] Code changes allowed (`Scoped support/frontend state-machine runtime + contract changes`)
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind the scoped frontdesk state-machine task and record the current contract/readlist.
2) Update the authoritative support/session contracts so states, slots, interrupts, and non-goals are singular and explicit.
3) Add a frontdesk state-machine module plus session-state persistence in the support runtime.
4) Wire the prompt/reply path to consume the state machine rather than only ad hoc branch-local fields.
5) Add focused regressions for state derivation, style persistence, interrupt recovery, and runtime consumption.
6) Run focused tests.
7) Run `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
8) Record the first failure and minimal fix strategy if verify fails.
9) Prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made: 复用现有 `conversation_mode` 和 `visible_state`，把 frontdesk state machine 作为其上的任务协调层，而不是重写整个 support/frontend 流。
- Alternatives considered: 直接把用户给的 `00_master_flow.md` 到 `10_nl_to_task.md` 原样作为新 prompt 文件挂进 repo；不采纳，因为这会和现有单一 authority 冲突，形成并行流程。
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - none
- Issue memory decision: required; 这是用户可见 support/frontdesk 主线保持缺口，属于结构性 route/continuity 风险。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this change is a repo-local runtime/frontdesk refactor rather than a reusable external workflow asset; if later需要独立“frontdesk-state-machine rollout”工作流，再考虑 skillization。

## Results

- Files changed:
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
- Verification summary: focused py_compile + `test_frontdesk_state_machine.py` + `test_runtime_wiring_contract.py` + `test_support_bot_humanization.py` + `test_issue_memory_accumulation_contract.py` + `test_skill_consumption_contract.py` passed; final canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` returned `0` after queue/task/report closure sync, with lite replay summary at `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260317-205618`.
- Queue status update suggestion (`todo/doing/done/blocked`): done
