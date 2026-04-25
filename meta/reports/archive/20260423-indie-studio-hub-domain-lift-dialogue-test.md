# Demo Report - Archive

## Topic

- `Indie Studio Hub Domain Lift dialogue-driven execution test`
- Date: `2026-04-23`
- Final verdict: `NEEDS_REWORK`

## Summary

- The support-bot dialogue path did not reliably bind or route the requested task.
- In one session the request bound a run but routed to `wf_orchestrator_only` and blocked on `context_pack.json`.
- In a clean second session the request was classified as `STATUS_QUERY`, so no real task binding happened even though the reply text sounded like work had started.

## First Failure Point

- Dialogue entry routing and binding, not project generation itself.
