# Task - Indie Studio Production Hub rough-goal generation test

Archived from `meta/tasks/CURRENT.md` when switching to `ADHOC-20260423-indie-studio-hub-domain-lift-dialogue-test`.

## Summary

- Queue Item: `ADHOC-20260423-indie-studio-hub-generation-test`
- Final product-level verdict: `NEEDS_REWORK`
- Key outcome: CTCP completed the full internal generation/delivery path, but the result still collapsed into `team_task_pm_web` style coverage rather than a full Indie Studio Production Hub domain.
- Key repair landed during the task: `detect_project_type()` no longer lets default `generic_copilot` override stronger team-task signals.

## Run Evidence

- Run dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\indie-studio-hub-generation-test-20260423`
- Final bundle: `artifacts/final_project_bundle.zip`
- Evidence bundle: `artifacts/intermediate_evidence_bundle.zip`
- Verify report: `artifacts/verify_report.json`

## First Failure Point

- First product failure point after internal PASS: generated output delivered `team_task_pm_web` / Plane-lite-style task PM coverage instead of the full requested Indie Studio Production Hub domains, docs, and screenshot coverage.
