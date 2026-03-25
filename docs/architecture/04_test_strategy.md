# 04 Test Strategy

## Test Layers

- `tests/contracts`: schema and validation boundary tests
- `tests/backend`: backend service and event generation tests
- `tests/frontend`: frontend message handling and requirement handoff tests
- `tests/integration`: frontend-backend protocol integration tests

## Required Assertions

- backend rejects full raw chat history payload fields
- frontend submits structured DTO only
- question/answer loop is contract-driven
- result and failure events are renderable without backend internals leakage

## Existing Compatibility

Legacy runtime tests remain in `tests/test_*.py` and are still executed by canonical verify.
