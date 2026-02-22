# B035 contract-checks-schema-readme-gate

## Reason
- Validate schema presence and README local links contract.

## Behavior
- Trigger: verify_repo contract stage runs contract_checks.py.
- Inputs / Outputs: spec schemas and README links -> contract result.
- Invariants: Broken schema presence or broken README links are hard failures.

## Result
- Acceptance: contract_checks non-zero exit blocks verify_repo.
- Evidence: scripts/contract_checks.py
- Related Gates: contract_checks

