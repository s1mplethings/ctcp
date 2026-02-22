# B030 local-exec-contract-guardian-run

## Reason
- Execute local contract_guardian review generation.

## Behavior
- Trigger: Dispatcher selects local_exec for contract_guardian review_contract.
- Inputs / Outputs: policy + git diff summary -> reviews/review_contract.md and review json/logs.
- Invariants: Guardian execution must produce explicit APPROVE/BLOCK verdict with reasons.

## Result
- Acceptance: Contract guardian returns exec_failed when policy violations exist.
- Evidence: tools/providers/local_exec.py
- Related Gates: workflow_gate

