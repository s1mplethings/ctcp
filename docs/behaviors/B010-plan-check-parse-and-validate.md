# B010 plan-check-parse-and-validate

## Reason
- Plan contract parser and validator for RBR artifacts.

## Behavior
- Trigger: CLI execution of scripts/plan_check.py.
- Inputs / Outputs: PLAN/REASONS/EXPECTED_RESULTS + behavior index -> validation diagnostics.
- Invariants: Validation reads contracts only and does not mutate source files.

## Result
- Acceptance: Exit code is non-zero when required fields or references are invalid.
- Evidence: scripts/plan_check.py,tools/checks/plan_contract.py
- Related Gates: plan_check

