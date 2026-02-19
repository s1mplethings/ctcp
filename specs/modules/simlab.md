# SimLab

## Purpose
- Replay deterministic scenarios to lock repository behavior with evidence.

## Scope
- Scenario parsing, sandbox copy, step execution, assertions, summary output.

## Non-Goals
- Production execution orchestration.
- Replacing verify gates.

## Inputs
- `simlab/scenarios/*.yaml` (JSON-or-YAML docs).
- repository sandbox copy.

## Outputs
- `${CTCP_RUNS_ROOT}/<repo_slug>/simlab_runs/<id>/summary.json`
- per-scenario `TRACE.md`, logs, optional failure bundle.

## Dependencies
- Scenario schema/assertion utilities.
- External runs-root path contract.

## Gates
- `python simlab/run.py --suite lite`
- optional full/integration suites.

## Failure Evidence
- Failed scenario must emit trace and bundle with logs/artifacts snapshots.

## Owner Roles
- Local Verifier / local test harness.
