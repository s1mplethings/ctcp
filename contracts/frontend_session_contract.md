# Frontend Session Contract (Non-Authoritative Frontdesk State)

This contract defines conversational session data boundaries for the frontend/support gateway.
If this file conflicts with `docs/00_CORE.md`, `docs/00_CORE.md` wins.

## Purpose

Session state supports task continuity, frontdesk state transitions, style persistence, and interruption recovery without replacing CTCP engineering truth.

The frontend/support lane is a task frontdesk, not a free-reply chat shell.
It must first resolve frontdesk state, then choose reply strategy, then emit user-visible text.

## Hard Boundary

Session data must never be treated as authoritative for:

- run status
- gate outcome
- verify result
- patch or artifact completion
- unresolved/fulfilled decision state

Authoritative state is always read from CTCP run artifacts through the approved bridge path.

## Required Frontdesk State Snapshot

Each session record may cache a normalized `frontdesk_state` object with at least:

- `state`
- `interrupt_kind`
- `current_goal`
- `current_scope`
- `active_task_id`
- `waiting_for`
- `user_style_profile`
- `decision_points`
- `artifacts`
- `blocked_reason`
- `resumable_state`

This snapshot is non-authoritative coordination state only.
It exists to prevent the frontdesk from losing the task line between turns.

## Required Style Profile

`user_style_profile` must support at least:

- `language`
- `tone`
- `initiative`
- `verbosity`

Rules:

1. Style changes must persist across later turns until explicitly changed again.
2. Style updates must not overwrite `current_goal` or `current_scope`.
3. Style profile affects reply shaping only; it does not become engineering truth.

## Interrupt Classification

The frontdesk must classify latest-turn interruptions into the narrowest matching class:

- `clarify`
- `redirect`
- `override`
- `sidequest`
- `style_change`
- `status_query`
- `result_query`

Rules:

1. Interrupt classification must not clear the active task by default.
2. `style_change` only updates `user_style_profile` and preserves `resumable_state`.
3. `status_query` and `result_query` must prefer the existing bound task/run path over reopening intake.
4. `override` may replace the active line only when the latest turn explicitly supersedes it.
5. `sidequest` must remain bounded and must not silently replace the main task.

## State Definitions

The minimum supported frontdesk states are below.
These states decide reply strategy and memory handling; they do not replace CTCP run truth or bridge behavior.

### `Idle`

- purpose: no bound task line yet; only detect whether the latest turn opens work
- enter_conditions: no actionable task signal, no active task, or pure greeting/capability without continuation intent
- allowed_actions: classify intent, answer greeting/capability locally via support model, preserve prior resumable state without reusing it
- forbidden_actions: create or mutate project runs, ask planning questions, invent project progress
- exit_conditions: task signal appears or an existing task is explicitly resumed
- next_states: `IntentDetect`, `StyleAdjust`

### `IntentDetect`

- purpose: decide whether the latest turn is intake, follow-up, status/result query, style change, or interruption
- enter_conditions: a new user turn arrives and needs routing judgment
- allowed_actions: inspect latest turn, classify interrupt kind, choose whether existing task context is reusable
- forbidden_actions: skip straight to free-form reply without state decision
- exit_conditions: enough routing signal to choose the next coordination state
- next_states: `Collect`, `Clarify`, `Confirm`, `Execute`, `AwaitDecision`, `ReturnResult`, `InterruptRecover`, `StyleAdjust`, `Error`

### `Collect`

- purpose: capture the minimum task object needed to continue without reopening the whole intake every turn
- enter_conditions: task-like turn exists but the frontdesk still lacks a stable goal/scope
- allowed_actions: bind `current_goal/current_scope`, keep one highest-leverage clarification pending, open a run through the bridge when allowed
- forbidden_actions: ask generic or repeated intake questions when state already contains the answer
- exit_conditions: enough task structure exists to confirm or execute
- next_states: `Clarify`, `Confirm`, `Execute`, `Error`

### `Clarify`

- purpose: request exactly the blocking detail or mutually exclusive choice that prevents safe continuation
- enter_conditions: `waiting_for` is non-empty, decision is unresolved, or a real ambiguity blocks execution
- allowed_actions: ask one bounded question, state the default assumption, keep the main task active
- forbidden_actions: broad re-intake, multi-question interrogation, losing the already-bound goal
- exit_conditions: blocker resolved or a safe default is recorded
- next_states: `Confirm`, `Execute`, `AwaitDecision`, `Error`

### `Confirm`

- purpose: lock the current task line before or while it enters execution
- enter_conditions: goal/scope are sufficiently stable but the turn is still transitioning from intake/follow-up into execution
- allowed_actions: summarize current goal/scope, preserve resumable state, hand off to bridge-backed execution
- forbidden_actions: reopen intake from zero when the task is already bound
- exit_conditions: run is bound/advanced or a real blocker appears
- next_states: `Execute`, `Clarify`, `AwaitDecision`, `Error`

### `Execute`

- purpose: keep the currently bound task moving and reply from task progress rather than generic support shells
- enter_conditions: active task/run exists and no user decision is currently blocking
- allowed_actions: read bridge/run truth, surface grounded progress, preserve style profile, continue same task line
- forbidden_actions: reopen intake for ordinary follow-ups, discard resumable state, invent progress from chat memory
- exit_conditions: a decision is needed, a result is ready, an interruption must be recovered, or an error occurs
- next_states: `AwaitDecision`, `ReturnResult`, `InterruptRecover`, `Error`

### `AwaitDecision`

- purpose: surface an explicit decision gate to the user without hiding the current task line
- enter_conditions: run truth says user input is required, `decision_points` is non-empty, or the latest turn is a decision reply
- allowed_actions: ask the concrete decision question, show recommendation/impact, keep `active_task_id`
- forbidden_actions: continue claiming execution is unblocked, or bury the decision behind generic filler
- exit_conditions: user decision is captured and submitted
- next_states: `Execute`, `ReturnResult`, `Error`

### `ReturnResult`

- purpose: return concrete output/progress/result from the active task path
- enter_conditions: delivery/result/progress response is requested or available and bound to current task truth
- allowed_actions: explain completed work, current phase, deliverables, proof refs, and next optional step
- forbidden_actions: claim completion without artifact/run evidence, or revert to generic kickoff language
- exit_conditions: result delivered or the conversation returns to active execution/follow-up
- next_states: `Execute`, `InterruptRecover`, `Idle`, `Error`

### `InterruptRecover`

- purpose: handle off-mainline turns without losing the resumable main task
- enter_conditions: latest turn is an interruption against an existing active line
- allowed_actions: classify interruption, preserve `resumable_state`, decide whether to merge, defer, supersede, or answer locally
- forbidden_actions: silently drop the main task or restart the whole task from zero
- exit_conditions: interruption resolved and the frontdesk knows whether to resume or replace the main line
- next_states: `Execute`, `AwaitDecision`, `ReturnResult`, `Collect`, `StyleAdjust`, `Error`

### `StyleAdjust`

- purpose: persist a user-requested change in reply style without mutating task truth
- enter_conditions: latest turn changes language/tone/initiative/verbosity
- allowed_actions: update `user_style_profile`, preserve `resumable_state`, keep task slots intact
- forbidden_actions: clear active task or reinterpret style-only turns as new project intake
- exit_conditions: style profile updated
- next_states: `Idle`, `IntentDetect`, `Execute`, `InterruptRecover`

### `Error`

- purpose: record frontdesk-visible failure when routing/prompt/render/bridge cannot continue normally
- enter_conditions: runtime cannot safely determine or execute the next frontdesk step
- allowed_actions: expose the failing stage in user-safe form, preserve resumable state, point to the minimal next repair
- forbidden_actions: leak raw internal traces, pretend execution is healthy, or silently drop the task line
- exit_conditions: failure handled or retried into a valid frontdesk state
- next_states: `IntentDetect`, `Execute`, `AwaitDecision`, `ReturnResult`

## Persistence Rules

1. `frontdesk_state` must be written back to session state after each handled turn.
2. `resumable_state` must only point to a real prior coordination state, not a synthetic placeholder.
3. `decision_points` and `artifacts` may cache user-facing summaries, but their truth source remains the bound run artifacts.
4. Session state may be summarized/pruned, but `current_goal`, `active_task_id`, `user_style_profile`, and `resumable_state` must survive normal continuity turns.

## Frontend Behavior Contract

1. The frontend/support entrypoint must resolve frontdesk state before picking reply strategy.
2. Reply strategy must consume both frontdesk state and CTCP run truth when an active task exists.
3. `VisibleState` or UI presentation labels remain derived output only; they must not become a second workflow engine.
4. If state is ambiguous, the frontend must report bounded uncertainty and refresh from bridge status rather than inventing continuity from chat memory.

## Memory Limits, Privacy, and Safety

1. Session memory should stay bounded by count and size.
2. Attachment content should not be duplicated into session memory; keep references only.
3. Do not store secrets unless explicitly required by task flow.
4. Do not expose raw internal command traces in normal user responses.
