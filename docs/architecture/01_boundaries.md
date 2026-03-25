# 01 Boundaries

## Frontend (`apps/cs_frontend`)

Allowed:

- receive user messages
- maintain session state
- collect requirements
- submit structured job requests
- render backend events/questions/results

Forbidden:

- directly writing patch plans
- deciding verify/fix pipeline behavior
- sending full chat transcript as backend execution input

## Backend (`apps/project_backend`)

Allowed:

- create and track jobs
- execute analyze/planning/context/generation/verification/repair phases
- ask structured questions when required
- produce structured status/result/failure events

Forbidden:

- direct customer-style natural-language support rendering logic
- direct dependency on frontend channel adapters
- consuming full raw chat history payloads

## Contracts (`contracts`)

Allowed:

- schema
- enum
- version
- validation

Forbidden:

- business logic
- prompt logic
- renderer/state machine execution logic

## Shared (`shared`)

Allowed:

- logging
- ids
- time
- json helpers
- errors

Forbidden:

- business flow branching
- phase-specific execution logic
