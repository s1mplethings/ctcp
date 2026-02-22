# B026 dispatch-step-plan-draft-family

## Reason
- Map plan_draft/analysis/guardrails/review-block states to chair plan_draft.

## Behavior
- Trigger: Dispatch derive_request inspects plan_draft,analysis,guardrails and approve-review reasons.
- Inputs / Outputs: blocked planning gate -> chair/plan_draft request.
- Invariants: Planning artifacts remain run_dir-local and do not mutate repo code directly.

## Result
- Acceptance: Planning-related blocked states route to chair plan_draft action.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

