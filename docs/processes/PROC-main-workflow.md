# PROC-main-workflow

## Metadata

- type: process
- state: active
- owner: Chair/Planner
- created_at: 2026-03-10
- replaced_from: none
- replaced_by: none

## Purpose

Define the canonical markdown-governance workflow so document changes are state-driven, auditable, and non-destructive by default.

## Inputs

- user request
- `docs/00_CORE.md`
- `docs/10_REGISTRY.md`
- `docs/20_STATE_MACHINE.md`
- current task scope (`meta/tasks/CURRENT.md`)

## Outputs

- object-level doc changes
- registry state updates
- decision references for transitions
- verify/report evidence

## Required Steps

1. Read `docs/00_CORE.md`.
2. Read `docs/10_REGISTRY.md`.
3. Locate target object IDs and current state.
4. Validate allowed transition using `docs/20_STATE_MACHINE.md`.
5. Execute inheritance check for impacted objects.
6. Apply object/registry updates.
7. Run checks and verify gate.
8. Record evidence in `meta/reports/LAST.md`.

## State Transition Policy

- allowed_from: approved
- allowed_to:
  - deprecated

## Dependencies

- STRAT-inheritance-check
- RULE-no-direct-delete

## Compatibility

- Existing active objects remain authoritative until transition completion.
- Deprecated objects may serve compatibility only and cannot be promoted silently.

## Exit Criteria

- Registry and object files are consistent.
- Transition evidence is recorded.
- Verify command has executed and outcome is captured.
