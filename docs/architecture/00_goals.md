# 00 Goals

## Refactor Goal

This refactor separates one mixed runtime path into four layers:

- `apps/cs_frontend`: customer-facing dialogue and requirement handoff
- `apps/project_backend`: project generation execution orchestration
- `contracts`: schema/enums/version/validation only
- `shared`: pure cross-cutting utilities only

## Non-Goals

- No immediate multi-repo split
- No replacement of existing runtime scripts in one shot
- No behavior drift in existing support run path

## Success Criteria

- Frontend does not decide patch/verify/fix actions
- Backend does not consume full raw chat history
- Frontend/backend communicate only through structured contracts
- Frontend/backend/contracts/integration tests can run independently
