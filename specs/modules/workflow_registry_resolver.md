# Workflow Registry Resolver

## Purpose
- Select the best local workflow candidate for execution planning.

## Scope
- Resolver-first lookup from `workflow_registry` and local historical evidence.

## Non-Goals
- Replacing decision authority with web research output.

## Inputs
- goal text.
- `workflow_registry/index.json`
- optional local success history snapshots.

## Outputs
- `${run_dir}/artifacts/find_result.json` (`ctcp-find-result-v1`).

## Dependencies
- Resolver contract boundary in `docs/02_workflow.md`.

## Gates
- Lite resolver scenario.
- contract checks + verify_repo.

## Failure Evidence
- Missing or invalid resolver output blocks planning and must be explicit in gate state.

## Owner Roles
- Resolver under Chair policy.
