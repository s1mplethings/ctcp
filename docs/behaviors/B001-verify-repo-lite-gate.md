# B001 verify-repo-lite-gate

## Reason
- Run headless lite configure/build/ctest path.

## Behavior
- Trigger: Verifier invokes verify_repo.
- Inputs / Outputs: artifacts/PLAN.md and build toolchain -> lite build and ctest logs.
- Invariants: Never silently bypass lite verification without explicit skip message.

## Result
- Acceptance: verify_repo fails fast when lite stage fails.
- Evidence: scripts/verify_repo.ps1,scripts/verify_repo.sh
- Related Gates: lite

