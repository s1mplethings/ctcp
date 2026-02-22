# B019 dispatch-step-review-contract

## Reason
- Map contract review blocking state to contract_guardian request.

## Behavior
- Trigger: Dispatch derive_request inspects review_contract path.
- Inputs / Outputs: blocked contract review gate -> contract_guardian/review_contract request.
- Invariants: Contract review target path must remain reviews/review_contract.md.

## Result
- Acceptance: Contract review blocking state routes to guardian role only.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

