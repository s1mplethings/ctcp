# North Star (Single Repo Purpose)

This file is the only authoritative source for repository purpose.

## Repo Purpose

CTCP is a contract-first execution engine that turns change requests into auditable delivery.
Its core value is deterministic execution evidence, not conversational appearance.

## What This Repository Is

- A repository-level operating system for planning, implementation, verification, and evidence closure.
- A runtime that advances project execution through explicit artifacts and gates.
- A contract-governed environment where completion is proven, not inferred.

## What This Repository Is Not

- Not a chat-memory-driven engineering tracker.
- Not a frontend-only product prototype.
- Not a collection of independent flows where each module redefines project goals.

## Default Operating Mode

- Headless-first, contract-first, verify-gated.
- Repository work follows the canonical execution flow in [docs/04_execution_flow.md](docs/04_execution_flow.md).

## Canonical Execution Flow

- Canonical flow definition lives only in [docs/04_execution_flow.md](docs/04_execution_flow.md).

## Product Lanes / Subsystem Map

- Core execution lane: orchestrator, verification gates, run artifact contracts.
- Frontend interaction lane: conversation classification and user-facing rendering.
- Frontend bridge lane: frontend-to-execution API boundary.
- Support lane: user support interaction shell over runtime truth.
- Optional GUI lane: visualization and operator convenience only.

## Goal Freeze Rule

Implementation tasks MUST NOT silently redefine:

- repository purpose
- canonical execution flow
- current task purpose/scope

If any of these must change, open a contract-change style queue/task path first.

## Completion Rule

A change is complete only when all are true:

- reachable from intended upstream and consumed by intended downstream (`connected`)
- failures are captured/updated in issue memory when applicable (`accumulated`)
- claimed skill usage is observable at runtime, or explicit non-skill decision is recorded (`consumed`)
- final gate evidence is present in runtime truth artifacts
