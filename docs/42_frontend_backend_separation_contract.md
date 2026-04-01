# Frontend-Backend Separation Contract

This contract defines strict separation between:

1. Backend Runtime Layer
2. Support API / BFF Layer
3. Frontdesk / Support UI Layer

## 1) Backend Runtime Layer (execution truth owner)

Backend runtime exclusively owns:
- run/task lifecycle
- authoritative stage
- verify result
- decision lifecycle (`pending/submitted/consumed/...`)
- current/render snapshot production
- output artifact production and completion decision

Frontend/support layers must not replace backend runtime truth.

## 2) Support API / BFF Layer (interface adapter only)

BFF responsibilities:
- call formal backend interfaces
- map responses into stable frontend schemas
- maintain session binding and light transformation

BFF forbidden actions:
- file-peeking as primary truth (`RUN.json`, `outbox/*`, `verify_report.json`, `TRACE.md`)
- synthesizing execution truth from internal files
- generating pending decision rows outside backend decision interfaces

## 3) Frontdesk Render-Only Contract

Frontdesk is display/input orchestration only.

Allowed:
- collect user inputs
- upload artifacts
- render progress/decision/result from backend snapshots/interfaces

Forbidden:
- infer execution truth
- infer verify truth
- infer completion truth
- infer blocker truth

Frontdesk state machine must be display states only:
- `idle`
- `collecting_input`
- `showing_progress`
- `waiting_user_reply`
- `showing_decision`
- `showing_result`
- `showing_error`

## 4) Support Controller Role Contract

Support controller is orchestration-only:
- throttle
- dedupe
- outbound notification queue
- message selection

Support controller must not:
- become a workflow truth engine
- infer done/decision from mixed legacy fields
- override backend snapshot truth

## 5) Artifact Consumption Contract

Frontend/support must consume project outputs through formal interfaces:
- `list_output_artifacts`
- `get_output_artifact_meta`
- `read_output_artifact`

If completion display is needed, frontend/support must also consume:
- `get_render_state_snapshot`
- backend result event payload
- artifact manifest (when provided by backend/BFF)

Direct run-dir scanning for customer-visible completion is forbidden.

## 6) Decision Contract

Pending decisions must come only from:
- `list_pending_decisions`

Decision submission must go only through:
- `submit_decision`

Frontend/support cannot create local pending decision truth.

## 7) Done Contract

Frontend/support can display completion only when backend-facing evidence is explicit:
- render snapshot done signal
- result event and/or artifact manifest evidence
- output artifacts readable through formal artifact interfaces
