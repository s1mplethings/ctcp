# 05 Migration Plan

## Phase 1 (this patch)

- add four-layer monorepo structure
- add contracts and shared utilities
- add frontend/backend service facades with structured APIs
- add independent test suites for each layer

## Phase 2

- move more legacy script internals behind backend service boundaries
- progressively consume new frontend application path from channel adapters

## Phase 3

- evaluate extraction to multiple repositories if operationally justified
- keep protocol compatibility tests as migration gate

## Safety Rule

Every migration step must preserve canonical verify and keep compatibility wrappers until replacement is verified.
