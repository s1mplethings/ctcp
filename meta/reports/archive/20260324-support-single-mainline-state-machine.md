# Report - support-single-mainline-state-machine

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260324-support-single-mainline-state-machine.md`](archive/20260324-support-single-mainline-state-machine.md)
- Date: 2026-03-24
- Topic: Support 单主流程状态机（禁用 Telegram 快速脚手架旁路）

### Readlist

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
- `meta/tasks/TEMPLATE.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

### Plan

1. Bind new ADHOC task for single-mainline support flow enforcement.
2. Disable support-side Telegram fast scaffold trigger and keep bridge state-machine mainline only.
3. Lock policy in support contract doc and local operator notes.
4. Add focused regression proving fast-path trigger is disabled.
5. Run focused checks and canonical verify; record first failing gate and minimal repair.

### Changes

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

### Verify

- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` -> `0`
- `$env:PYTHONPATH='tests'; python -m unittest -v test_support_bot_humanization.SupportBotHumanizationTests.test_t2p_fast_path_trigger_is_disabled_for_project_create_turn` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `1`
- first failure point (focused runtime wiring suite): preexisting branch baseline failures in `frontend/response_composer.py` (`IndexError`) and `run_stdin_mode` StringIO buffer handling; not introduced by this scoped change.
- minimal fix strategy (focused runtime wiring suite): isolate and repair existing frontend/state fixture assumptions and stdin wrapper robustness in a dedicated task before expecting full suite green.
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point: `patch check (scope from PLAN)` with `out-of-scope path (Scope-Allow): test_final.py`
- minimal fix strategy: remove or relocate unrelated preexisting `test_final.py` from worktree (or explicitly bind/include it in scoped PLAN) and rerun canonical verify.

### Questions

- None.

### Demo

- Support runtime now enforces single mainline behavior for project-create turns:
  - `should_trigger_t2p_state_machine(...)` is hard-disabled
  - project turns stay on `ctcp_front_bridge` bind/record/advance path only
- Contract update in `docs/10_team_mode.md` now states fast scaffold side path is forbidden and `gate=blocked` cannot emit delivery-complete semantics.
- Local operator note (`.agent_private/NOTES.md`) now records the same single-mainline hard rule for runtime ops.

### Integration Proof

- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `should_trigger_t2p_state_machine` trigger gate
- downstream: `sync_project_context` bridge flow + `build_final_reply_doc`
- source_of_truth: bound run `status.gate` / `status.run_status` + support session state
- fallback: no fast-path fallback; blocked gate yields grounded status/next-step messaging only
- acceptance_test:
  - `python -m py_compile ...`
  - focused support fast-path-disable unittest
  - canonical `scripts/verify_repo.ps1`
- forbidden_bypass:
  - no Telegram ingress scaffold side route
  - no support-layer state fabrication
  - no prompt-only fix
- user_visible_effect: user no longer gets “quick package-ready” path detached from main run gate progression.
