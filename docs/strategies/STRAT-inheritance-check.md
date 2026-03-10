# STRAT-inheritance-check

## Metadata

- type: strategy
- state: active
- owner: Chair/Planner
- created_at: 2026-03-10
- replaced_by: none

## Purpose

Ensure new or revised objects preserve required intent from existing active objects and do not silently shift repository goals.

## Required Inheritance Checklist

For every modified object, document:

- inherited_rules: which existing rules remain effective
- retained_behavior: which behaviors are unchanged
- replaced_behavior: which behaviors are intentionally replaced
- goal_stability: why this is implementation/flow evolution, not purpose shift
- compatibility_delta: any compatibility removed and why
- migration_path: how existing users move to replacement objects

## Execution Timing

- Must run before `proposed -> approved`.
- Must be referenced in transition decision records.
- Must be reflected in `docs/10_REGISTRY.md` when state changes.

## Success Criteria

- no hidden rule loss
- no silent goal shift
- explicit replacement mapping for changed active objects
- verify/report evidence captured
