# B006 verify-repo-contract-checks-gate

## Reason
- Run repository contract integrity checks.

## Behavior
- Trigger: Verifier invokes contract_checks gate.
- Inputs / Outputs: schema files and README links -> contract check result.
- Invariants: Do not allow broken schema presence or broken local README links.

## Result
- Acceptance: contract_checks must exit non-zero on contract violations.
- Evidence: scripts/contract_checks.py
- Related Gates: contract_checks

