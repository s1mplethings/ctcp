# Demo Report - Support Single Project-Generation Interface (Mainline)

## Readlist
- `AGENTS.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md` (archived topic)
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_front_bridge.py`
- `docs/10_team_mode.md`
- `docs/backend_interface_contract.md`
- `tests/test_support_chain_breakpoints.py`
- `tests/test_project_turn_mainline_contract.py`

## Plan
1. Add one bridge-side support project-turn sync interface to unify create/bind/record/advance.
2. Route support runtime project turns to that single interface.
3. Fix previous-project status routing so unbound status-like followups do not create new runs.
4. Remove support process-time fast-path invocation branch.
5. Update mainline md contracts to document the single interface rule.
6. Run targeted regressions + workflow/verify gates and record first failure point/minimal fix.

## Changes
- Added `ctcp_sync_support_project_turn` / `sync_support_project_turn` unified interface in bridge.
- Support runtime switched to unified sync path for project turn + recovery.
- Previous-project followup routing stabilized to `STATUS_QUERY` even when unbound.
- Mainline docs/contracts updated for single support entry.

## Verify
- `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v` -> PASS
- `python -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v` -> PASS
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> PASS
- `python scripts/workflow_checks.py` -> PASS
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only` -> PASS

## Questions
- None.

## Demo
- support 项目型 turn 统一走 bridge 单入口；状态追问不再误触发新 run 创建。