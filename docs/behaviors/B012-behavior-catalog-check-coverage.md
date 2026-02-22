# B012 behavior-catalog-check-coverage

## Reason
- Catalog checker for BEHAVIOR_ID markers and docs coverage.

## Behavior
- Trigger: CLI execution of scripts/behavior_catalog_check.py.
- Inputs / Outputs: marker scan + docs index/pages -> coverage verdict.
- Invariants: All required entry files must contain explicit BEHAVIOR_ID markers.

## Result
- Acceptance: Exit code is non-zero on missing mapping or missing section headers.
- Evidence: scripts/behavior_catalog_check.py,docs/behaviors/INDEX.md
- Related Gates: behavior_catalog_check

