# UX Flow

## Primary User Flow

1. User gives a project goal.
2. CTCP creates Virtual Team planning artifacts.
3. Source_generation records intent/spec/library/file manifest evidence.
4. Provider-authored files are materialized from normalized `path` / `content` rows.
5. Library usage verification and smoke checks decide pass or blocked.
6. Delivery surfaces either the final package path or a precise blocking reason.

## Key States

- `ready_for_source_generation`: output contract and context pack exist.
- `provider_source_missing`: no provider-authored source rows; production is blocked.
- `provider_source_materialized`: files are written and provenance is recorded.
- `library_policy_failed`: generated files violate required imports, forbidden patterns, syntax, runtime commands, or placeholders.
- `delivery_allowed`: provider authorship and validation gates pass.

## Success Path

The user receives a generated MVP only when source files, library plan, manifest, verification, smoke checks, and provenance all agree.

## Failure Path

When checks fail, CTCP records the first file/task/library violation and blocks final delivery while keeping intermediate evidence available.
