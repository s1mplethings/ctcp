# Frontend Bridge Contract (CTCP Front Gateway)

This contract defines the only allowed bridge surface between conversational frontend code and CTCP execution.
If this file conflicts with `docs/00_CORE.md`, `docs/00_CORE.md` wins.

## Scope

The frontend bridge is a thin adapter layer.
It can:

- accept user intent and attachment metadata
- call CTCP orchestrator entrypoints
- read run artifacts and report summaries
- expose decision prompts to the conversational UI

It cannot:

- edit repository source files
- generate patch content
- run `scripts/verify_repo.ps1` or `scripts/verify_repo.sh`
- invent task state from chat memory
- mutate run state except by orchestrator commands or explicit run-artifact submission APIs below

## Allowed Operations (Only)

Frontend code may only call these bridge operations:

1. `ctcp_new_run(goal, constraints, attachments)`
2. `ctcp_get_status(run_id)`
3. `ctcp_advance(run_id, max_steps)`
4. `ctcp_get_last_report(run_id)`
5. `ctcp_list_decisions_needed(run_id)`
6. `ctcp_submit_decision(run_id, decision)`
7. `ctcp_upload_artifact(run_id, file)`

No additional execution control operation is allowed.

## Truth Source Rules

1. Authoritative engineering state is the CTCP run package:
   - `RUN.json`
   - `events.jsonl`
   - `TRACE.md`
   - `artifacts/*`
2. Frontend session memory is non-authoritative context cache only.
3. Any status claim shown to user must be derivable from run artifacts.
4. Completion claims require artifact evidence (for example `artifacts/verify_report.json` with `result=PASS`).

## Status Rendering Rules

Presentation states are UI-only and must be derived from CTCP outputs:

- `CREATED`
- `ANALYZING`
- `PLANNING`
- `WAITING_FOR_USER`
- `EXECUTING`
- `VERIFYING`
- `BLOCKED`
- `DONE`

These labels must not become a second workflow engine.

## Decision Routing Rules

1. Decision requests must be read from `outbox/*.md` and/or `QUESTIONS.md` in run_dir.
2. `ctcp_submit_decision` must write only the requested target artifact for that pending decision.
3. Decision submission must not bypass CTCP gate progression; next execution still uses `ctcp_advance`.
4. Missing required decision data must be surfaced to the user as a bounded question, not auto-invented.

## Attachment Intake Rules

1. Uploaded files are copied into run_dir artifact space.
2. Frontend must not copy uploads into repository code directories.
3. Upload metadata can be cached in session memory, but file truth remains run_dir artifacts.
