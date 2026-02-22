# B025 dispatch-step-fixer-patch

## Reason
- Map fixer-owned patch blocking/fail to fixer patch flow.

## Behavior
- Trigger: Dispatch derive_request inspects diff.patch path with fixer owner.
- Inputs / Outputs: blocked/fail gate -> fixer/fix_patch request.
- Invariants: Fixer patch target path must stay artifacts/diff.patch.

## Result
- Acceptance: Fixer route preserves patch-only retry contract.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

