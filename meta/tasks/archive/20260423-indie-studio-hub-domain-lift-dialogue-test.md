# Task - Indie Studio Hub Domain Lift dialogue-driven execution test

Archived from `meta/tasks/CURRENT.md` when switching to `ADHOC-20260423-dialogue-entry-routing-and-binding-fix`.

## Summary

- Queue Item: `ADHOC-20260423-indie-studio-hub-domain-lift-dialogue-test`
- Final verdict: `NEEDS_REWORK`
- Key outcome: CTCP could say plausible progress words, but the dialogue entry either misrouted the task to `wf_orchestrator_only` or classified a full Domain Lift request as `STATUS_QUERY`, leaving no real bound run in the second clean session.

## Evidence

- Session 1: `%TEMP%\ctcp_runs\ctcp\support_sessions\indie-domain-lift-dialogue-20260423`
- Session 1 bound run: `%TEMP%\ctcp_runs\ctcp\20260423-171017-837045-orchestrate`
- Session 2: `%TEMP%\ctcp_runs\ctcp\support_sessions\indie-domain-lift-dialogue-round2-20260423`

## First Failure Point

- The dialogue entry misclassified and misbound the request:
  - session 1 selected `wf_orchestrator_only` for a Domain Lift / rerun generation repair request
  - session 2 classified the request as `STATUS_QUERY`, leaving `active_goal`, `bound_run_id`, and `bound_run_dir` empty
