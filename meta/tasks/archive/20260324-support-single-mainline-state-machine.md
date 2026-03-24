# Task - support-single-mainline-state-machine

## Queue Binding

- Queue Item: `ADHOC-20260324-support-single-mainline-state-machine`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户要求“只要一个主流程”，禁止 support 快速生成旁路。
- Dependency check: `ADHOC-20260317-support-frontdesk-state-machine` = `done`.
- Scope boundary: 只修 support lane runtime wiring 与合同文档，不改 orchestrator/bridge 核心实现。

## Task Truth Source (single source for current task)

- task_purpose: enforce single mainline state-machine flow for support project turns.
- allowed_behavior_change: `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`, `.agent_private/NOTES.md`, `tests/test_support_bot_humanization.py`, `meta/*task/report*`.
- forbidden_goal_shift: no bridge bypass, no parallel fast ingress generation path, no canonical verify skip.
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `.agent_private/NOTES.md`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-single-mainline-state-machine.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-single-mainline-state-machine.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `frontend/frontdesk_state_machine.py`
  - `src/`
  - `include/`
- completion_evidence: project-create turn no longer fires support t2p fast path; docs and tests lock single-mainline policy.

## Analysis / Find (before plan)

- Entrypoint analysis: `process_message()` currently may trigger `run_t2p_state_machine()` on project-create intent.
- Downstream consumer analysis: this can inject package-ready behavior before main run gate becomes ready.
- Source of truth: `docs/00_CORE.md` bridge/state-machine contracts + `docs/10_team_mode.md` support lane contract.
- Current break point / missing wiring: dual-path behavior causes quick reply vs blocked mainline mismatch.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: support message ingress (`telegram`/`stdin`) via `process_message()`.
- current_module: `should_trigger_t2p_state_machine` guard and related runtime branch.
- downstream: bridge-backed `sync_project_context` and final reply/action generation.
- source_of_truth: bound run `status.gate`, `status.run_status`, support session state.
- fallback: if gate blocked, keep grounded status reply only; no fast path package claims.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - no Telegram fast-path scaffold side route
  - no support-layer state fabrication
  - no prompt-only workaround
- user_visible_effect: one visible flow only, aligned with frontdesk + bridge state machine.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: support runtime no longer triggers support-side Telegram ingress scaffold fast path; project turns only enter the bridge-backed mainline run flow
- [x] DoD-2: auto-advance and delivery behavior are strictly gated by bound-run status/gate state machine instead of standalone fast-path pass signals
- [x] DoD-3: docs and local operator notes explicitly codify single-mainline policy and focused regressions prove fast-path trigger is disabled

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan)
- [x] Code changes allowed (`Scoped support runtime wiring update`)
- [ ] Patch applies cleanly (blocked by unrelated preexisting out-of-scope path `test_final.py`)
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind task + queue.
2) Disable fast scaffold trigger path.
3) Keep bridge/state-machine mainline as sole project flow.
4) Add focused regression for disabled trigger.
5) Update contracts/docs + local operator notes.
6) Run focused tests + canonical verify.
7) Record first failure point and minimal repair strategy.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: runtime evidence showed fast scaffold state machine reports emitted before mainline gate advanced.
  - contrast-1: user-visible behavior diverged from single-mainline expectation.
  - fix-1: remove fast-path trigger and lock policy in docs/tests.
  - check-2: run focused tests and canonical verify, then patch first failing gate only if needed.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: ingress -> bridge mainline -> reply path only.
  - accumulated: session/run status artifacts remain single source.
  - consumed: user-visible actions consume mainline state only.

## Notes / Decisions

- Default choices made: prioritize deterministic single-mainline correctness over fast first reply.
- Alternatives considered: keep fast path with copy tweaks (rejected).
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: this class (dual-path user-visible mismatch) should stay tracked as support wiring risk.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded runtime wiring correction.
- persona_lab_impact: none.

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-single-mainline-state-machine.md`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `docs/10_team_mode.md`
  - `.agent_private/NOTES.md`
  - `ai_context/problem_registry.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-single-mainline-state-machine.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `$env:PYTHONPATH='tests'; python -m unittest -v test_support_bot_humanization.SupportBotHumanizationTests.test_t2p_fast_path_trigger_is_disabled_for_project_create_turn` => `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `1` (baseline unrelated failures)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1` (patch check: out-of-scope path `test_final.py`)
- Queue status update suggestion (`todo/doing/done/blocked`): blocked
