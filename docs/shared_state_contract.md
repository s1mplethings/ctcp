# Shared State Contract

## Purpose

`shared state workspace` is the only cross-layer communication hub for frontend/frontdesk/bridge/runtime/support state exchange.

It is not a new execution authority. Runtime/orchestrator/verifier remain the engineering truth authority.

## Authoritative State vs Visible State

Two state layers are mandatory and must not be mixed:

- Authoritative runtime state (`authoritative_stage`)
  - `NEW`
  - `INTAKE`
  - `PLANNING`
  - `WAITING_DECISION`
  - `EXECUTING`
  - `VERIFYING`
  - `BLOCKED`
  - `DONE`
  - `FAILED`
- Visible state (`visible_state`)
  - `UNDERSTOOD`
  - `NEEDS_ONE_OR_TWO_DETAILS`
  - `EXECUTING`
  - `WAITING_FOR_DECISION`
  - `BLOCKED_NEEDS_INPUT`
  - `DONE`

Visible state is a render layer for frontend/frontdesk/support shell. It must not overwrite authoritative runtime truth.

## Event Stream and Snapshots

Shared workspace layout:

- `shared_state/schemas/`
- `${workspace_root}/tasks/<task_id>/events.jsonl`
- `${workspace_root}/tasks/<task_id>/current.json`
- `${workspace_root}/tasks/<task_id>/render.json`
- `${workspace_root}/tasks/<task_id>/locks/`

Rules:

- `events.jsonl` is append-only.
- `current.json` is rebuilt from event replay.
- `render.json` is derived from `current.json`.
- Normal write path is: append event -> rebuild current -> refresh render.
- Direct arbitrary overwrite of `current.json` is forbidden.

## Event Model

Each event must contain:

- `ts`
- `task_id`
- `type`
- `source`
- `payload`

Minimum supported event types:

- `user_message`
- `conversation_mode_detected`
- `user_decision_recorded`
- `authoritative_stage_changed`
- `blocker_changed`
- `next_action_set`
- `verification_result_recorded`
- `render_state_refreshed`

## Snapshot Model

`current.json` minimum fields:

- `task_id`
- `authoritative_stage`
- `visible_state`
- `conversation_mode`
- `current_task_goal`
- `known_facts`
- `missing_fields`
- `last_confirmed_items`
- `current_blocker`
- `blocking_question`
- `next_action`
- `proof_refs`
- `verify_result`

`render.json` minimum fields:

- `task_id`
- `ui_badge`
- `reply_style`
- `followup_questions`
- `decision_cards`
- `visible_state`
- `progress_summary`
- `proof_refs`

## Support Bridge Canonical Snapshot

For support/frontdesk/frontend bridge reads, runtime status MUST also be exposed as one stable run-local snapshot:

- `${run_dir}/artifacts/support_runtime_state.json`

This snapshot is the canonical bridge read model. `RUN.json`, `verify_report.json`, orchestrate status output, `outbox/`, and `QUESTIONS.md` may only be used as compatibility fallback inputs to refresh this snapshot.

`support_runtime_state.json` minimum fields:

- `phase`
- `run_status`
- `blocking_reason`
- `needs_user_decision`
- `pending_decisions`
- `latest_result`
- `error`
- `recovery`
- `updated_at`

Decision object minimum fields:

- `decision_id`
- `kind`
- `question`
- `target_path`
- `expected_format` or `schema`
- `status` (`pending|submitted|consumed|rejected|expired`)
- `created_at`
- `submitted_at`
- `consumed_at`

Bridge rule:

- Decision write success means `submitted`, not `consumed`.
- Runtime progression confirmation requires either:
  - decision status transitions to `consumed`, or
  - canonical runtime snapshot core state advances after submission.

## Write Permissions

Write permissions are strict and source-scoped:

1. frontend/frontdesk can write:
   - `user_message`
   - `conversation_mode_guess`
   - `user_decision`
   - `clarification_answer`
   - `ui_feedback`
2. runtime/orchestrator can write:
   - `authoritative_stage`
   - `execution_status`
   - `current_blocker`
   - `next_action`
   - `proof_refs`
   - `verify_result`
   - `last_confirmed_items`
3. verifier can write:
   - `verification_events`
   - `failure_reason`
   - `evidence_paths`
4. UI renderer/support shell:
   - read `render.json` only
   - must not write `authoritative_stage`, `verify_result`, or done flags

## Forbidden Actions

- UI/support shell directly deciding `DONE` from ad-hoc file checks.
- Response generation layer acting as runtime truth authority.
- Any module bypassing event append and mutating authoritative state directly.
- Letting visible state overwrite authoritative stage.
- Declaring completion when verify/proof evidence is missing.

## Backend Interface Binding

Shared-state snapshots are necessary but not sufficient.

Beyond snapshot files, integration must use formal backend interfaces for:

- run creation/advance/status
- pending decision listing/submission
- input artifact upload
- output artifact/image enumeration and read
- current/render snapshot reads

See:

- `docs/backend_interface_contract.md`
