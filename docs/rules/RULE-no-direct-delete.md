# RULE-no-direct-delete

## Metadata

- type: rule
- state: active
- owner: Contract Guardian
- created_at: 2026-03-10
- replaced_by: none

## Purpose

Prevent silent removal of active processes, strategies, interfaces, rules, and implementations.

## Rule Statement

- Active objects must not be removed directly.
- Any removal must follow state transitions in `docs/20_STATE_MACHINE.md`.
- Direct transitions from `active` to `removed` or `archived` are forbidden.

## Required Preconditions Before Deprecation

- replacement target identified, or explicit no-replacement rationale.
- dependency scan completed.
- no-new-usage policy documented.

## Required Preconditions Before Removal

- repo references are zero.
- config references are zero.
- compatibility path is disabled and isolated.
- verify gate has run with captured evidence.

## Required Evidence

- `docs/10_REGISTRY.md` updated in same patch.
- decision reference recorded for each state transition.
- summary in `meta/reports/LAST.md`.

## Failure Policy

- If preconditions are missing, the transition is blocked.
- Blocked transitions remain at current state and must not be force-applied.
