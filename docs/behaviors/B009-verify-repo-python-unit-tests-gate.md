# B009 verify-repo-python-unit-tests-gate

## Reason
- Execute Python unit-test gate.

## Behavior
- Trigger: Verifier invokes python unit-test discover stage.
- Inputs / Outputs: tests/test_*.py -> unittest exit status.
- Invariants: Unit tests remain mandatory in verify_repo default path.

## Result
- Acceptance: unittest failure must fail verify_repo.
- Evidence: scripts/verify_repo.ps1,scripts/verify_repo.sh
- Related Gates: python_unit_tests

