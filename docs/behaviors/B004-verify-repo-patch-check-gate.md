# B004 verify-repo-patch-check-gate

## Reason
- Enforce changed-file scope from PLAN scope fields.

## Behavior
- Trigger: Verifier invokes patch_check gate.
- Inputs / Outputs: git changed paths + PLAN scope -> scope pass/fail.
- Invariants: Missing/unparseable PLAN is always a failure for patch_check.

## Result
- Acceptance: patch_check blocks any changed path outside Scope-Allow or in Scope-Deny.
- Evidence: scripts/patch_check.py,artifacts/PLAN.md
- Related Gates: patch_check

