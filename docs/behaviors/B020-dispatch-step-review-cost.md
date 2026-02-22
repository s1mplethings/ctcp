# B020 dispatch-step-review-cost

## Reason
- Map cost review blocking state to cost_controller request.

## Behavior
- Trigger: Dispatch derive_request inspects review_cost path.
- Inputs / Outputs: blocked cost review gate -> cost_controller/review_cost request.
- Invariants: Cost review target path must remain reviews/review_cost.md.

## Result
- Acceptance: Cost review blocking state routes to cost_controller role.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

