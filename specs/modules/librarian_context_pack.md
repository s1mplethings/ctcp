# Librarian Context Pack

## Purpose
- Provide minimal, budgeted repo context for planning/execution roles.

## Scope
- Read `ctcp-file-request-v1` and write `ctcp-context-pack-v1`.
- Enforce file and byte budgets.

## Non-Goals
- Planning or strategy decisions.
- Repo mutation.

## Inputs
- `${run_dir}/artifacts/file_request.json`
- repo files referenced by request `needs[]`.

## Outputs
- `${run_dir}/artifacts/context_pack.json`
- budget summary and omission reasons.
- optional `knowledge_summary` metadata for API-efficient local knowledge consumption.
- optional per-file metadata such as `role_hint`, `relevance_summary`, `compression_hint`, `must_follow_rules`, and `avoid_patterns`.

## Boundary
- Librarian output is evidence and context, not task assignment.
- Chair/Planner and routed Virtual Team stages remain responsible for project direction, task split, and implementation decisions.
- Librarian must not introduce project-specific templates or generate production source as proof.

## Dependencies
- File-request contract.
- Repo path safety checks.

## Gates
- Lite context-pack scenarios (blocked and local_exec paths).
- `scripts/verify_repo.*` pass.

## Failure Evidence
- Invalid request schema or budget errors must be explicit in stderr/logs.
- Omitted files must include reason categories.

## Owner Roles
- Local Librarian only.
