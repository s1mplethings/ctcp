# 02 Contracts

## Protocol Version

`contracts/version.py` defines the protocol version string.

## Request Schemas

- `job_create.py`: structured create-job request with explicit requirement summary
- `job_answer.py`: structured answer for backend questions

## Event Schemas

- `event_status.py`
- `event_question.py`
- `event_result.py`
- `event_failure.py`

## Validation Rules

`contracts/validation.py` enforces:

- required field presence
- object/list type safety
- full-chat-history field rejection for backend execution input

This keeps frontend/backend communication deterministic and audit-friendly.
