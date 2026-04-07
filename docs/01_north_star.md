# North Star (Single Repo Purpose)

This file is the only authoritative source for repository purpose.

## Repo Purpose

CTCP is a goal-to-MVP generation system that turns vague user requests into structured intent, runnable projects, and verifiable delivery.
Its core value is not “process correctness by itself”, but a trustworthy mainline:
`goal understanding -> project generation -> runnable validation -> evidence retention`.

## What This Repository Is

- A repository-level system for understanding user goals, shaping them into `ProjectIntent`, generating runnable MVP projects, and validating delivery.
- A runtime that advances project generation through explicit stages instead of pretending that manifests/gates are the product.
- A contract-governed environment where evidence supports generation truth instead of replacing it.
- A system that keeps production execution persona, test user personas, and scoring/judge logic separated so style regressions can be reproduced and scored.

## What This Repository Is Not

- Not a chat-memory-driven engineering tracker.
- Not a frontend-only product prototype.
- Not an artifact-first shell where verify/manifest can impersonate a generated MVP.

## Delivery Qualities

- Task advancement stays bound to one current goal instead of restarting from chat tone every turn.
- Test capability includes test-plan generation, test-case generation, execution evidence, and user-visible demo traces.
- Style regression capability includes isolated persona cases, structured transcripts, judge scores, and fail reasons instead of ad hoc “natural enough” checks.
- Version and provenance data flow from one authority (`VERSION`) into reports and generated outputs.
- User-visible replies must be task-progressive and artifact-grounded, not reception-desk scripts.

## Default Operating Mode

- Intent-first, MVP-first, verify-supported.
- Repository work enters through [AGENTS.md](../AGENTS.md) and uses [docs/04_execution_flow.md](docs/04_execution_flow.md) only as the expanded workflow reference.

## Workflow Reference

- Root agent contract lives in [AGENTS.md](../AGENTS.md).
- Expanded workflow details live in [docs/04_execution_flow.md](docs/04_execution_flow.md).

## Product Lanes / Subsystem Map

- Core generation lane: `ProjectIntent -> Spec -> Scaffold -> Core Feature -> Smoke Run -> Delivery Package`.
- Frontend interaction lane: intent modeling and user-facing understanding summary.
- Shared state workspace lane: append-only cross-layer state hub (`events -> current -> render`) with runtime-authoritative ownership.
- Frontend bridge lane: frontend-to-execution API boundary.
- Support lane: user support interaction shell over runtime truth.

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
