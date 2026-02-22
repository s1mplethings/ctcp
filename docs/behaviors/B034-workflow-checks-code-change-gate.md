# B034 workflow-checks-code-change-gate

## Reason
- Detect forbidden code edits when task contract is not enabled.

## Behavior
- Trigger: verify_repo workflow gate runs workflow_checks.py.
- Inputs / Outputs: git changed files + CURRENT.md checkbox -> pass/fail.
- Invariants: Code directories cannot change without [x] Code changes allowed.

## Result
- Acceptance: workflow_checks blocks verify_repo on unauthorized code edits.
- Evidence: scripts/workflow_checks.py,meta/tasks/CURRENT.md
- Related Gates: workflow_gate

