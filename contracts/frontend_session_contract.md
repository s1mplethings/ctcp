# Frontend Session Contract (Non-Authoritative Memory)

This contract defines conversational session data boundaries for the frontend gateway.

## Purpose

Session state supports conversational continuity (tone, user context, recent turns) without replacing CTCP engineering truth.

## Session Model

Each session record may store:

- `user_id`
- `session_id`
- `project_key`
- `bound_run_id`
- `messages` (bounded recent history)
- `attachments` (upload references)
- `last_seen_presentation_state`
- timestamps (`created_at`, `updated_at`)

## Hard Boundary

Session data must never be treated as authoritative for:

- run status
- gate outcome
- verify result
- patch or artifact completion
- unresolved/fulfilled decision state

Authoritative state is always read from CTCP run artifacts.

## Memory Limits

1. Session memory should be bounded by count and size.
2. Messages may be summarized/pruned; engineering facts must be re-read from CTCP artifacts.
3. Attachment content should not be duplicated into session memory; keep path/reference metadata only.

## Privacy and Safety

1. Session cache should be kept outside repository source tree by default.
2. Do not store secrets unless explicitly required by task flow.
3. Do not expose raw internal command traces in normal user responses.

## Frontend Behavior Contract

1. If CTCP says blocked and decisions are pending, frontend asks targeted decision question.
2. If no pending decision, frontend reports current stage and next expected step.
3. If state is ambiguous, frontend must report uncertainty and refresh from bridge status.
