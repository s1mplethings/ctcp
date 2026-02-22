# B008 verify-repo-lite-replay-gate

## Reason
- Replay lite scenario set as repository smoke gate.

## Behavior
- Trigger: Verifier invokes lite scenario replay.
- Inputs / Outputs: simlab suite and fixtures -> replay status and logs.
- Invariants: Replay skip is allowed only via explicit CTCP_SKIP_LITE_REPLAY contract.

## Result
- Acceptance: lite replay failure must fail verify_repo.
- Evidence: scripts/verify_repo.ps1,scripts/verify_repo.sh
- Related Gates: lite_replay

