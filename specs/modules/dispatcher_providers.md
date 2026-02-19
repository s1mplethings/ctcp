# Dispatcher Providers

## Purpose
- Resolve blocked artifacts into role-appropriate provider actions.

## Scope
- Map gate state -> role/action/target artifact.
- Invoke `manual_outbox` or constrained `local_exec`.

## Non-Goals
- Network/API execution.
- Override artifact contract boundaries.
- Replace resolver authority.

## Inputs
- `${run_dir}/artifacts/dispatch_config.json`
- current gate state from orchestrator.
- role templates under `agents/prompts/*` (manual provider).

## Outputs
- `${run_dir}/outbox/*.md` prompts for manual/API roles.
- provider execution events in `${run_dir}/events.jsonl`.

## Dependencies
- Orchestrator state machine.
- Role contract docs and artifact contracts.

## Gates
- Lite dispatch scenarios (missing review -> outbox, librarian local_exec path).
- `scripts/verify_repo.*` pass.

## Failure Evidence
- Dispatcher failures must be visible in events and trace.
- Budget-exceeded path must be explicit and reproducible.

## Owner Roles
- Local Orchestrator dispatches.
- Local Librarian allowed for `local_exec`.
- API roles are manual-outbox only.
