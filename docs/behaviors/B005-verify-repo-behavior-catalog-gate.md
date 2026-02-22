# B005 verify-repo-behavior-catalog-gate

## Reason
- Enforce BEHAVIOR_ID coverage against docs/behaviors catalog.

## Behavior
- Trigger: Verifier invokes behavior_catalog_check gate.
- Inputs / Outputs: code markers + docs/behaviors/INDEX.md -> catalog pass/fail.
- Invariants: Every scanned marker must map to exactly one documented behavior entry.

## Result
- Acceptance: behavior_catalog_check fails on missing marker docs or missing required sections.
- Evidence: scripts/behavior_catalog_check.py,docs/behaviors/INDEX.md
- Related Gates: behavior_catalog_check

