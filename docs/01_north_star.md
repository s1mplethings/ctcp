# North Star (Single Repo Purpose)

This file is the only authoritative source for repository purpose.

## Repo Purpose

CTCP is a contract-first execution system that turns change requests into auditable delivery.
Its core value is deterministic execution evidence. User-visible dialogue, tests, demos, and persona regressions exist to expose that evidence, not to replace it.

## What This Repository Is

- A repository-level operating system for planning, implementation, verification, test design, and evidence closure.
- A runtime that advances project execution through explicit artifacts, fixed mainline stages, and user-visible demo outputs.
- A contract-governed environment where completion is proven, explained, and shown from the same truth sources.
- A system that keeps production execution persona, test user personas, and scoring/judge logic separated so style regressions can be reproduced and scored.

## What This Repository Is Not

- Not a chat-memory-driven engineering tracker.
- Not a frontend-only product prototype.
- Not a collection of independent flows where each module redefines project goals.

## Delivery Qualities

- Task advancement stays bound to one current goal instead of restarting from chat tone every turn.
- Test capability includes test-plan generation, test-case generation, execution evidence, and user-visible demo traces.
- Style regression capability includes isolated persona cases, structured transcripts, judge scores, and fail reasons instead of ad hoc “natural enough” checks.
- Version and provenance data flow from one authority (`VERSION`) into reports and generated outputs.
- User-visible replies must be task-progressive and artifact-grounded, not reception-desk scripts.

## Default Operating Mode

- Headless-first, contract-first, verify-gated.
- Repository work enters through [AGENTS.md](../AGENTS.md) and uses [docs/04_execution_flow.md](docs/04_execution_flow.md) only as the expanded workflow reference.

## Workflow Reference

- Root agent contract lives in [AGENTS.md](../AGENTS.md).
- Expanded workflow details live in [docs/04_execution_flow.md](docs/04_execution_flow.md).

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
- user-visible explanation and showcase remain grounded in the same task/run truth used by engineering artifacts
