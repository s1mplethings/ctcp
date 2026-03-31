# Backend Interface Contract

## Baseline

- repo: `s1mplethings/ctcp`
- branch: `main`
- baseline commit: `81f8f35`
- version: `3.3.0`

This contract defines backend interfaces used for:

- standalone backend testing
- frontdesk/support integration
- file and image input/output verification
- shared-state snapshot reads

This document is additive to:

- `docs/shared_state_contract.md`
- `docs/frontend_runtime_boundary.md`

Runtime/orchestrator/verifier still own execution truth.

## Existing-Compatible Interfaces

The following interfaces must remain compatible with baseline behavior:

- `create_run`
- `get_run_status`
- `advance_run`
- `list_pending_decisions`
- `submit_decision`
- `upload_input_artifact`
- `get_last_report`
- `get_support_context`
- `record_support_turn`

### 1) `create_run`

Purpose:

- create run
- persist request context (goal/constraints/attachments)

Minimum response:

- `run_id`
- `run_dir`
- `created`
- `status`

### 2) `get_run_status`

Purpose:

- return backend status snapshot directly consumable by frontdesk/support

Minimum fields:

- `run_id`
- `run_dir`
- `run_status`
- `verify_result`
- `verify_gate`
- `iterations`
- `gate`
- `needs_user_decision`
- `decisions_needed_count`
- `latest_status_raw`

### 3) `advance_run`

Purpose:

- advance execution by controlled backend steps

Rules:

- supports `max_steps >= 1`
- response must include refreshed `status`

### 4) `list_pending_decisions`

Purpose:

- list user-visible blocking decisions

Decision row minimum:

- `decision_id`
- `kind`
- `question` or `question_hint`
- `target_path`
- `status`

### 5) `submit_decision`

Purpose:

- submit user decision payload for a pending decision

Rules:

- lookup by `decision_id` must be supported
- JSON targets must be validated
- `submitted` does not mean `consumed`
- write success cannot be treated as backend-consumed progress

### 6) `upload_input_artifact`

Purpose:

- upload user inputs into run workspace

Rules:

- support generic files
- prevent path escape outside run workspace
- uploaded artifacts are available to run-scoped request context

### 7) `get_last_report`

Purpose:

- read latest report and verify outputs

### 8) `get_support_context`

Purpose:

- expose stable support/frontdesk read context

### 9) `record_support_turn`

Purpose:

- persist support-facing turns for replay/audit

## Recommended New Interfaces

For standalone backend testing, add formal interfaces:

- `list_output_artifacts`
- `get_output_artifact_meta`
- `read_output_artifact`
- `get_current_state_snapshot`
- `get_render_state_snapshot`

### Output Artifact Interfaces

`list_output_artifacts` must enumerate all run outputs, including images.

`get_output_artifact_meta` must return stable metadata (at minimum type/mime/size/path).

`read_output_artifact` must provide formal read/download access, including image outputs.

Tests must not rely only on ad-hoc directory scanning.

### Snapshot Interfaces

`get_current_state_snapshot` returns authoritative/current shared state view.

`get_render_state_snapshot` returns render-facing state view consumed by frontdesk/support.

## Decision Lifecycle Contract

Decision lifecycle is explicit:

1. `pending`
2. `submitted`
3. `consumed`
4. `rejected`
5. `expired`

Decision object minimum:

- `decision_id`
- `kind`
- `question`
- `target_path`
- `expected_format` or `schema`
- `status`
- `created_at`
- `submitted_at`
- `consumed_at`

Hard rule:

- `submitted` is not `consumed`.
- frontdesk/support cannot claim execution resumed only from submit write success.

## Image Input/Output Requirements

### Input Images

Input images must use generic artifact upload (`upload_input_artifact`), same path as normal files.

### Output Images

Output images must be formal backend outputs:

- enumerable via `list_output_artifacts`
- metadata-readable via `get_output_artifact_meta`
- content-readable via `read_output_artifact`

## Acceptance Criteria

Backend interface layer is acceptable only if:

1. run can be created
2. files and images can be uploaded
3. status can be read
4. run can be advanced
5. decisions can be listed/submitted
6. last report can be read
7. output artifacts and images can be enumerated/read
8. current/render snapshots can be read
9. `submitted` is not treated as `consumed`
