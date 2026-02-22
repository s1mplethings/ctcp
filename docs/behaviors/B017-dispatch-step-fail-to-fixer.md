# B017 dispatch-step-fail-to-fixer

## Reason
- Map fail state to fixer patch request.

## Behavior
- Trigger: Dispatch derive_request handles state=fail.
- Inputs / Outputs: gate fail state -> fixer/fix_patch request payload.
- Invariants: Fail state cannot bypass fixer target path artifacts/diff.patch.

## Result
- Acceptance: Fail state always resolves to fixer request contract.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

