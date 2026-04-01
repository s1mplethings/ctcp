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
- complete project repository delivery checks

This document is additive to:

- `docs/shared_state_contract.md`
- `docs/frontend_runtime_boundary.md`
- `docs/41_low_capability_project_generation.md`

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

## Required Output and Snapshot Interfaces

The following interfaces are mandatory for project-generation completion checks:

- `list_output_artifacts`
- `get_output_artifact_meta`
- `read_output_artifact`
- `get_project_manifest`
- `get_current_state_snapshot`
- `get_render_state_snapshot`

If event transport is enabled, frontend/support should consume:
- `poll_events` or `stream_events`

### Output Artifact Interfaces

`list_output_artifacts` must enumerate all run outputs, including images.

`get_output_artifact_meta` must return stable metadata (at minimum kind/mime/size/path/readability).

`read_output_artifact` must provide formal read/download access, including image outputs.

`get_project_manifest` must return project-level completeness metadata, not only raw file listing.

Tests must not rely only on ad-hoc directory scanning.

### `get_project_manifest` minimum response

- `run_id`
- `project_id`
- `source_files`
- `doc_files`
- `workflow_files`
- `generated_files`
- `missing_files`
- `acceptance_files`
- `reference_project_mode`
- `reference_style_applied`
- `artifacts` (enumerable refs for source/doc/workflow/image/resource outputs)

`reference_project_mode` minimum fields:

- `enabled` (bool)
- `mode` (`structure_only|workflow_only|docs_only|structure_workflow_docs`)

### Snapshot Interfaces

`get_current_state_snapshot` returns authoritative/current shared state view.

`get_render_state_snapshot` returns render-facing state view consumed by frontdesk/support.

Hard binding:

- current snapshot is runtime truth.
- render snapshot is display truth.
- frontdesk/support cannot infer completion from raw directory scans.
- BFF/bridge adapters cannot rebuild truth by scanning internal run files as a primary source.

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
- present in `get_project_manifest.artifacts`

## ResultEvent Binding

Final result objects/events MUST include explicit artifact inventory.

Minimum requirement:

- include `artifacts` list with references covering source/doc/workflow layers
- include manifest reference (`project_manifest` path/ref)
- include `reference_project_mode` and `reference_style_applied` when enabled

Summary-only result events are not acceptable for project-generation completion.

## Acceptance Criteria

Backend interface layer is acceptable only if:

1. run can be created
2. files and images can be uploaded
3. status can be read
4. run can be advanced
5. decisions can be listed/submitted
6. last report can be read
7. output artifacts and images can be enumerated/read
8. project manifest can be read and includes source/doc/workflow layer inventories
9. current/render snapshots can be read
10. `submitted` is not treated as `consumed`

## Hard DONE Conditions for Project Generation

Project-generation completion can be marked done only when all conditions hold:

1. Source layer complete.
2. Documentation layer complete.
3. Agent workflow layer complete.
4. Key outputs enumerable through formal artifact interface.
5. Key outputs readable through formal artifact interface.
6. ResultEvent includes explicit artifact list.
7. If reference mode enabled, output structure reflects declared reference style.
8. Not report-only output.
9. Not partial-code-as-full-completion.
10. Minimum closed-loop project repository delivered for low-capability path.
