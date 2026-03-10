# Registry (Single Source of Markdown Object State)

This file is the single authority for current object state in the Markdown governance lane.

Registry rules:
- Every governed object must have a unique ID and one canonical entry.
- Runtime/default behavior may only consume objects with `state: active`.
- Transition legality is defined by `docs/20_STATE_MACHINE.md`.
- State changes must be backed by a decision record and reflected here in the same patch.

## Object Types

- process
- strategy
- interface
- rule
- implementation

## State Values

- draft
- proposed
- approved
- active
- deprecated
- disabled
- removed
- archived
- rejected

## Active Objects

### PROC-main-workflow

- type: process
- state: active
- owner: Chair/Planner
- replaced_by: none
- depends_on:
  - STRAT-inheritance-check
  - RULE-no-direct-delete
- entry_doc: docs/processes/PROC-main-workflow.md
- decision_ref: DEC-2026-03-010
- last_verified: 2026-03-10
- notes: canonical markdown-governance workflow in docs lane

### STRAT-inheritance-check

- type: strategy
- state: active
- owner: Chair/Planner
- replaced_by: none
- depends_on:
  - RULE-no-direct-delete
- entry_doc: docs/strategies/STRAT-inheritance-check.md
- decision_ref: DEC-2026-03-010
- last_verified: 2026-03-10
- notes: guards against silent goal shift and hidden rule loss

### RULE-no-direct-delete

- type: rule
- state: active
- owner: Contract Guardian
- replaced_by: none
- depends_on: []
- entry_doc: docs/rules/RULE-no-direct-delete.md
- decision_ref: DEC-2026-03-010
- last_verified: 2026-03-10
- notes: forbids direct removal of active objects

## Migration Notes

- New objects must start at `draft` and follow allowed transitions only.
- `deprecated` objects can stay for compatibility but cannot become default again without a formal transition.
- `removed` objects must have zero repository/config references before moving to `archived`.
