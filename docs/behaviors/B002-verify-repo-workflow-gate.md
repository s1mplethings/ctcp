# B002 verify-repo-workflow-gate

## Reason
- Run workflow prerequisite checks before contract checks.

## Behavior
- Trigger: Verifier invokes workflow gate in verify_repo.
- Inputs / Outputs: git diff and meta/tasks/CURRENT.md -> workflow pass/fail.
- Invariants: Code changes are forbidden unless CURRENT.md explicitly allows them.

## Result
- Acceptance: workflow_checks non-zero exit blocks verify_repo.
- Evidence: scripts/workflow_checks.py
- Related Gates: workflow_gate

