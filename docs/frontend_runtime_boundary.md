# Frontend Runtime Boundary

## Frontend/Frontdesk Can Understand

Frontend/frontdesk can understand:

- conversation mode and user intent
- task-progress explanation for user-visible replies
- visible state and follow-up questions from render state
- user decisions and clarification answers

Frontend can shape user-facing wording, but cannot decide execution truth.

## Runtime Is the Execution Authority

Only runtime/orchestrator/verifier can decide:

- authoritative stage transitions
- verify pass/fail outcomes
- blocker ownership and execution next action truth
- completion/delivery readiness bound to proof evidence

Completion claims are valid only when runtime verify result and proof refs are aligned.

## Support Shell Rule

Support shell must read `render truth` only:

- read `render.json`
- do not infer completion from random run files
- do not mutate authoritative stage fields
- do not bypass shared-state permission rules

If render state says not done, support shell cannot announce done.

## Why User Explanation Is Not Engineering Truth

User-visible explanation is necessary but not sufficient:

- explanation can be fluent but still wrong
- engineering closure requires artifact-backed proof
- runtime truth and user-visible reply must come from the same task/run evidence chain

Therefore:

- frontend reply generation consumes shared `current/render` snapshots
- runtime still owns authoritative state and verify evidence
- support wording does not replace engineering truth

## Backend Interface Binding

Frontend/frontdesk/support must bind formal backend interfaces, not temporary file scans or ad-hoc state guessing.

Required integration anchor:

- `docs/backend_interface_contract.md`

This includes stable backend reads/writes for run lifecycle, decisions, artifact I/O, and shared current/render snapshots.
