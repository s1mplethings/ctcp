# Orchestrator

## Purpose
- Advance ADLC by artifact-state gates without taking planning authority.

## Scope
- `new-run`, `status`, `advance` lifecycle.
- Gate transitions, event emission, verify triggering, failure closure.

## Non-Goals
- Decide workflow strategy.
- Author business patch content.
- Approve plans/reviews.

## Inputs
- `${run_dir}/artifacts/*`
- `${run_dir}/reviews/*`
- `${run_dir}/RUN.json`
- repo contracts and verify entrypoint.

## Outputs
- `${run_dir}/RUN.json` status updates.
- `${run_dir}/events.jsonl`, `${run_dir}/TRACE.md`.
- verify and failure artifacts (`verify_report`, `failure_bundle`).

## Dependencies
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- verify gate scripts.

## Gates
- SimLab lite orchestrator scenarios.
- `scripts/verify_repo.*` pass.

## Failure Evidence
- Must preserve `TRACE.md`, `events.jsonl`, `artifacts/verify_report.json`.
- Must generate/validate `failure_bundle.zip` on verify fail.

## Owner Roles
- Local Orchestrator (write control-plane artifacts/events).
- Local Verifier (write verify and failure evidence events).
