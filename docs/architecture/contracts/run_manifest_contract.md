# Run Manifest Contract

## Purpose

`run_manifest.json` is the run-level truth source for the default CTCP mainline.
It proves that Librarian, ADLC, Whiteboard, and Bridge evidence belongs to the same run instead of being inferred from separate artifacts.

`run_responsibility_manifest.json` is the single responsibility ledger for that same run.
It is the only accountability surface for goal/entry/workflow/provider/API/fallback/final-producer/final-verdict fields.

## Location

`${run_dir}/artifacts/run_manifest.json`
`${run_dir}/artifacts/run_responsibility_manifest.json`

## Schema Version

`ctcp-run-manifest-v1`
`ctcp-run-responsibility-manifest-v1`

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

## Responsibility Ledger Required Fields

| Field | Meaning |
|---|---|
| `raw_user_goal` | Original user goal from `RUN.json`. |
| `chosen_entry` | Formal run entrypoint. |
| `chosen_workflow` | Selected workflow id (`find_result`). |
| `bound_run_id` | Bound run id. |
| `bound_run_dir` | Bound run directory absolute path. |
| `stage_owners` | Owner map for critical mainline stages. |
| `provider_used_per_critical_stage` | Provider map by critical stage. |
| `external_api_used_per_critical_stage` | External API usage map by critical stage. |
| `fallback_used` | Whether fallback occurred on critical stages. |
| `final_code_producer` | Final code producer provider. |
| `final_doc_producer` | Final doc producer provider. |
| `internal_runtime_status` | Runtime completion status. |
| `user_acceptance_status` | User-facing acceptance status. |
| `first_failure_point` | First failure point when not fully passing. |
| `final_verdict` | `PASS` / `PARTIAL` / `NEEDS_REWORK`. |

## Writers

- `scripts/ctcp_librarian.py` updates context-pack presence and context-pack failure.
- `scripts/ctcp_orchestrate.py` updates ADLC phase, gate status, final status, and first failure fields.
- `scripts/workflows/adlc_self_improve_core.py` reports its ADLC phases into the same contract.
- `tools/adlc_gate.py` reports pass/fail when it can infer a run directory.
- `scripts/ctcp_dispatch.py` updates whiteboard presence after support/dispatch whiteboard writes.
- `scripts/ctcp_front_bridge.py` updates bridge presence and bridge output refs when frontend/support consumes run state.

## Reader Rule

Any user-visible claim that the default mainline ran through Librarian, ADLC, Whiteboard, and Bridge should be backed by this manifest first, then by the detailed artifacts referenced by the manifest.
Any user-visible claim about provider accountability, API-only compliance, status split, or verdict must be backed by `run_responsibility_manifest.json`.

## Failure Rule

If a run fails, `first_failure_gate` and `first_failure_reason` must be populated by the runtime layer that observes the failure.
If the run has not failed, those fields remain empty.
