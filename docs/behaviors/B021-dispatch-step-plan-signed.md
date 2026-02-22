# B021 dispatch-step-plan-signed

## Reason
- Map PLAN sign-off blocking state to chair plan_signed request.

## Behavior
- Trigger: Dispatch derive_request inspects PLAN.md path.
- Inputs / Outputs: blocked plan gate -> chair/plan_signed request.
- Invariants: Signed plan must target artifacts/PLAN.md exactly.

## Result
- Acceptance: Plan sign-off blocking state routes to chair role.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

