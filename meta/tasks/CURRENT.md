# Task - provider-automation-core-roles

## Queue Binding
- Queue Item: `N/A (user-directed provider automation task)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- Upgrade core roles from manual outbox to executable providers with minimal invasive changes.
- Keep offline reproducibility by leaving researcher web-find path manual.
- Ensure verify gate catches new provider tests through `unittest discover`.

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: `contract_guardian` auto-exec provider outputs contract review artifacts and blocks with explicit reasons.
- [x] DoD-2: `patchmaker`/`fixer` use `api_agent` provider to emit plan+patch artifacts with command/env-driven execution.
- [x] DoD-3: provider selection defaults are configured in workflow recipe and dispatch fallback remains backward compatible.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local implementation)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first
2) Implement provider + dispatch changes
3) Verify (`python -m unittest discover` + `verify_repo`)
4) Record (decision/problem logs if needed)
5) Demo (`LAST.md` + run trace pointer)

## Notes / Decisions
- No new third-party dependencies; Python stdlib only.
- `local_exec` remains restricted to safe built-in local roles (`librarian`, `contract_guardian`).
- `api_agent` supports both external command templates (`SDDAI_*_CMD`) and OPENAI env fallback wrappers.

## Results
- Added `tools/providers/api_agent.py` with evidence-pack generation and deterministic command execution logs.
- Extended `tools/providers/local_exec.py` to auto-run contract guardian checks.
- Updated dispatch to recognize `api_agent`, merge recipe defaults, and keep config override priority.
- Added provider selection and E2E tests; full verify gates passed.
