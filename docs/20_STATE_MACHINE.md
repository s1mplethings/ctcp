# Markdown Object State Machine

This file defines the only allowed transition graph for markdown-governed objects.

## States

- draft
- proposed
- approved
- active
- deprecated
- disabled
- removed
- archived
- rejected

## Allowed Transitions

- `draft -> proposed`
- `proposed -> approved`
- `approved -> active`
- `active -> deprecated`
- `deprecated -> disabled`
- `disabled -> removed`
- `removed -> archived`
- `draft -> rejected`
- `proposed -> rejected`

## Forbidden Direct Jumps

- `active -> removed`
- `active -> archived`
- `deprecated -> archived`
- Any transition not listed in "Allowed Transitions"

## Transition Requirements

### draft -> proposed

Required:
- initial object spec
- scoped impact note
- affected object list

### proposed -> approved

Required:
- inheritance check completed
- impact analysis completed
- decision draft prepared

### approved -> active

Required:
- implementation/spec merged
- verify gate executed
- registry updated to active

### active -> deprecated

Required:
- replacement target or explicit "no replacement" rationale
- dependency scan completed
- no-new-usage policy documented

### deprecated -> disabled

Required:
- default-off behavior documented
- compatibility path isolated
- warning/deprecation note present

### disabled -> removed

Required:
- repo_ref_count == 0
- config_ref_count == 0
- tests migrated or retired with decision
- verify gate executed

### removed -> archived

Required:
- archive record created
- decision log updated

## Runtime Interpretation

- `active`: usable as canonical/default behavior.
- `deprecated`: allowed only for compatibility, never for new default paths.
- `disabled`: not callable in default path.
- `removed`: must not exist in code/config references.
- `archived`: historical record only.
