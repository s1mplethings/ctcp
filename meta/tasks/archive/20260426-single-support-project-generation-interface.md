# Task Archive - Support Single Project-Generation Interface (Mainline)

## Queue Binding

- Queue Item: `ADHOC-20260426-single-support-project-generation-interface`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Status: `done`

## Scope Summary

- support runtime 项目 turn 统一改为一个 bridge 接口 `ctcp_sync_support_project_turn`
- 旧项目状态追问在未绑定 run 场景下也走 `STATUS_QUERY`
- 文档合同同步单入口主线规则

## Key Changes

- `scripts/ctcp_front_bridge.py`
  - added unified support sync interface `ctcp_sync_support_project_turn`
- `scripts/ctcp_support_bot.py`
  - switched project-turn sync/recovery to unified bridge interface
  - removed support-side split create/record/advance mutation path in process mainline
  - tightened previous-project status routing
- `docs/10_team_mode.md`, `docs/backend_interface_contract.md`
  - declared support project-turn single-entry contract
- `tests/test_support_chain_breakpoints.py`, `tests/test_project_turn_mainline_contract.py`
  - added/updated regressions for routing and mainline interface usage

## Verify

- `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v` -> PASS
- `python -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v` -> PASS
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> PASS
- `python scripts/workflow_checks.py` -> PASS
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only` -> PASS