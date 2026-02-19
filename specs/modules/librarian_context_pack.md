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
