# B003 verify-repo-plan-check-gate

## Reason
- Validate PLAN/REASONS/EXPECTED_RESULTS machine-readable contracts.

## Behavior
- Trigger: Verifier invokes plan_check gate.
- Inputs / Outputs: artifacts/PLAN.md + artifacts/REASONS.md + artifacts/EXPECTED_RESULTS.md -> plan validation result.
- Invariants: Plan fields must remain parseable key lines.

## Result
- Acceptance: plan_check reports missing fields/ids as hard failures.
- Evidence: scripts/plan_check.py,artifacts/PLAN.md
- Related Gates: plan_check

