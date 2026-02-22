# B024 dispatch-step-patchmaker

## Reason
- Map diff.patch blocking to patchmaker make_patch flow.

## Behavior
- Trigger: Dispatch derive_request inspects diff.patch path with non-fixer owner.
- Inputs / Outputs: blocked patch gate -> patchmaker/make_patch request.
- Invariants: Patch target path must stay artifacts/diff.patch.

## Result
- Acceptance: Patchmaker route is used only for non-fixer patch generation.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

