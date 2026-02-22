# Dispatcher Providers

## Purpose
- Resolve blocked artifacts into role-appropriate provider actions.

## Scope
- Map gate state -> role/action/target artifact.
- Invoke `manual_outbox`, `api_agent`, or constrained `local_exec`.
- When patch-first gate rejects `artifacts/diff.patch`, dispatch fixer retry with patch-only constraints.

## Non-Goals
- Unrestricted shell/network execution outside configured provider command templates.
- Override artifact contract boundaries.
- Replace resolver authority.

## Inputs
- `${run_dir}/artifacts/dispatch_config.json`
- current gate state from orchestrator.
- role templates under `agents/prompts/*` (manual provider).
- evidence pack inputs for `api_agent`:
  - `${run_dir}/outbox/CONTEXT.md`
  - `${run_dir}/outbox/CONSTRAINTS.md`
  - `${run_dir}/outbox/FIX_BRIEF.md`
  - `${run_dir}/outbox/EXTERNALS.md`

## Outputs
- `${run_dir}/outbox/*.md` prompts for manual/API roles.
- provider execution events in `${run_dir}/events.jsonl`.
- Rejection feedback paths in outbox prompt metadata (for example `reviews/review_patch.md`).
- `api_agent` default artifacts:
  - `${run_dir}/outbox/PLAN.md`
  - `${run_dir}/outbox/diff.patch`

## Dependencies
- Orchestrator state machine.
- Role contract docs and artifact contracts.

## Gates
- Lite dispatch scenarios (missing review -> outbox, librarian local_exec path).
- `scripts/verify_repo.*` pass.

## Failure Evidence
- Dispatcher failures must be visible in events and trace.
- Budget-exceeded path must be explicit and reproducible.
- Patch rejection retry loop must keep candidate patch + reject reason auditable.

## Owner Roles
- Local Orchestrator dispatches.
- `local_exec` is restricted to `librarian` and `contract_guardian`.
- `api_agent` is allowed for patch roles (`patchmaker`, `fixer`) and must keep explicit logs.
