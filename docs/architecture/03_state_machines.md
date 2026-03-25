# 03 State Machines

## Frontend Dialogue State

Frontend maintains conversational state only:

- mode routing (greeting/smalltalk/project/status)
- session memory summary
- pending question tracking
- presentable reply rendering

## Backend Execution State

Backend tracks execution phase only:

- created
- generation/verification/repair lifecycle
- waiting_answer when a decision is required
- done/failed terminal states

## Separation Rule

Frontend state transitions never mutate backend internal phase decisions directly.
Backend phase transitions never depend on raw frontend chat transcripts.
