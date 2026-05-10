# Task Archive - Live API Project Pipeline Test

## Queue Binding

- Queue Item: `ADHOC-20260510-live-api-project-pipeline-test`
- Layer/Priority: `L1 / P0`
- Lane: `Delivery Lane`
- Date: `2026-05-10`

## Scope

- Run a bounded live API project-generation pipeline test.
- Inspect provider ledger, source_generation, and verify evidence.
- Do not manually patch generated project files.

## Run Evidence

- Run dir: `D:\.c_projects\adc\ctcp_runs\ctcp\live-api-project-pipeline-20260510`
- Status: `running`, blocked at `artifacts/source_generation_report.json`.
- Blocker: `generic_validation.passed must be true`.

## Provider Evidence

- `critical_step_count=11`
- `critical_api_step_count=11`
- `all_critical_steps_api=true`
- `fallback_count=0`
- `failed_count=0`

## Source Evidence

- `generated_files=29`
- `missing_files=0`
- `business_files_generated=9`
- `business_files_missing=0`
- `source_customization_completion.final_delivery_allowed=true`
- `generic_validation.passed=false`
- `gate_layers.structural.passed=true`
- `gate_layers.behavioral.passed=false`
- `gate_layers.result.passed=false`

## First Failure

- Export probe returned `rc=1`.
- Python signature consistency failed:
  - generated test calls `export_project_assets` with one positional argument.
  - implementation requires `export_project_assets(service_inst, out_dir)`.
  - interface metadata has eight declared-vs-actual signature mismatches.
- UX validation failed because visual evidence files and preview source page were missing.
- `artifacts/verify_report.json` is absent because the run did not reach verify.

## Commands

- PASS: `new-run --run-id live-api-project-pipeline-20260510` created the external run.
- FIRST FAILURE: `advance --max-steps 24` timed out after 20 minutes, after reaching source_generation.
- PASS: `status` reported the source_generation generic validation blocker.
- FIRST FAILURE: continuation `advance --max-steps 4` timed out after 15 minutes and did not add a new ledger row.

## Decision

- experiment_result: partial success.
- merge_decision: no code merge from this task.
- next repair: strengthen API source_generation retry/handoff for export command behavior, signature metadata consistency, and visual evidence artifacts.
