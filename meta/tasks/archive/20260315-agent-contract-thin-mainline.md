# Task Archive - 2026-03-15 - 薄主合同 + 单流程 + 局部覆盖的 agent 规则收口

Queue Item: `ADHOC-20260315-agent-contract-thin-mainline`
Status: `done`

## Summary

- Simplify root agent rules into a thin main contract.
- Collapse the visible agent mainline to Bind / Read / Analyze / Change / Verify-Close.
- Move local concerns out of root `AGENTS.md` without creating a new heavy instructions hierarchy.

## Scope

- root `AGENTS.md`
- `README.md`
- `docs/04_execution_flow.md`
- direct conflict entry docs
- minimal `.github/instructions/`

## Key Constraints

- simplify, do not expand
- one root agent authority only
- keep README human-oriented
- do not change business code, tests, or CI behavior

## Acceptance

- root `AGENTS.md` is shorter and clearer
- `README.md` no longer acts as an agent authority map
- `docs/04_execution_flow.md` is explanatory, not the root contract
- direct conflicts are aligned and contract-profile verify passes
