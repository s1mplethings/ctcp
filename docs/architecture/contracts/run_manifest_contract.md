# Run Manifest Contract

## Purpose

`run_manifest.json` is the run-level truth source for the default CTCP mainline.
It proves that Librarian, ADLC, Whiteboard, and Bridge evidence belongs to the same run instead of being inferred from separate artifacts.

## Location

`${run_dir}/artifacts/run_manifest.json`

## Schema Version

`ctcp-run-manifest-v1`

## Required Fields

| Field | Meaning |
|---|---|
| `run_id` | Run directory identity. |
| `workflow_name` | Mainline workflow name, normally `ctcp_default_mainline`. |
| `execution_lane` | Lane currently reporting into the ADLC mainline. |
| `context_pack_present` | Whether `artifacts/context_pack.json` exists and has been observed. |
| `context_pack_path` | Relative context pack path. |
| `adlc_phase` | Current ADLC phase or lane gate phase. |
| `adlc_plan_present` | Whether a signed or lane-equivalent plan artifact exists. |
| `adlc_gate_status` | Current gate status as reported by orchestration. |
| `whiteboard_present` | Whether `artifacts/support_whiteboard.json` exists and has been observed. |
| `whiteboard_path` | Relative whiteboard path. |
| `bridge_present` | Whether a frontend/support bridge interaction has been observed. |
| `bridge_output_present` | Whether the bridge produced or consumed a client-visible payload. |
| `bridge_output_refs` | Relative refs or interface names consumed through the bridge. |
| `delivery_artifacts` | User-facing delivery artifact refs when available. |
| `gates_passed` | Gates that have passed in this run. |
| `first_failure_gate` | First failing gate for failed runs. Empty for non-failed runs. |
| `first_failure_reason` | Human-readable first failure reason. Empty for non-failed runs. |
| `final_status` | Current/final status: `created`, `running`, `blocked`, `fail`, `pass`, or lane-specific equivalent. |
| `updated_at` | UTC update timestamp. |

## Writers

- `scripts/ctcp_librarian.py` updates context-pack presence and context-pack failure.
- `scripts/ctcp_orchestrate.py` updates ADLC phase, gate status, final status, and first failure fields.
- `scripts/workflows/adlc_self_improve_core.py` reports its ADLC phases into the same contract.
- `tools/adlc_gate.py` reports pass/fail when it can infer a run directory.
- `scripts/ctcp_dispatch.py` updates whiteboard presence after support/dispatch whiteboard writes.
- `scripts/ctcp_front_bridge.py` updates bridge presence and bridge output refs when frontend/support consumes run state.

## Reader Rule

Any user-visible claim that the default mainline ran through Librarian, ADLC, Whiteboard, and Bridge should be backed by this manifest first, then by the detailed artifacts referenced by the manifest.

## Failure Rule

If a run fails, `first_failure_gate` and `first_failure_reason` must be populated by the runtime layer that observes the failure.
If the run has not failed, those fields remain empty.
