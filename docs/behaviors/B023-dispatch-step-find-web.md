# B023 dispatch-step-find-web

## Reason
- Map resolver_plus_web research blocking to researcher action.

## Behavior
- Trigger: Dispatch derive_request inspects find_web/externals paths.
- Inputs / Outputs: blocked research gate -> researcher/find_web request.
- Invariants: Research artifacts stay under run_dir artifacts/meta externals contract.

## Result
- Acceptance: Research blocking state routes to researcher role.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

