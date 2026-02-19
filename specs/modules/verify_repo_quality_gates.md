# Verify Repo Quality Gates

## Purpose
- Provide the single repository acceptance gate for merge-quality decisions.

## Scope
- Build/test (where available), workflow checks, contract checks, doc index check, lite replay.

## Non-Goals
- Replacing run-level verify evidence in external run_dir.

## Inputs
- repository working tree.
- `meta/tasks/CURRENT.md`, contract docs, scripts.

## Outputs
- process exit status (pass/fail) and actionable logs.

## Dependencies
- `scripts/workflow_checks.py`
- `scripts/contract_checks.py`
- `scripts/sync_doc_links.py --check`
- `simlab/run.py`.

## Gates
- `scripts/verify_repo.ps1` (Windows)
- `scripts/verify_repo.sh` (Unix)

## Failure Evidence
- Failures must pinpoint gate step and command-level cause.

## Owner Roles
- Local Verifier.
