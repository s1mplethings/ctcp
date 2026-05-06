# Task Archive - Provider Src Layout Runtime Probe

## Queue Binding

- Queue Item: `ADHOC-20260503-provider-src-layout-runtime-probe`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: latest VN run generated provider-authored source and retry succeeded, but `generic_validation` failed because runtime probes launched a `src/` layout GUI entrypoint without `PYTHONPATH`, and `asset_placeholders.json` was treated as placeholder-only content.
- Lane: Delivery Lane.
- Scope boundary: runtime probe compatibility and generic placeholder false positive only; no local business source generation.

## Task Truth Source

- task_purpose:
  - Runtime probes should execute generated src-layout GUI projects the same way users can run them locally.
  - GUI export probe should tolerate provider entrypoints that implement only `--headless`.
  - Asset placeholder catalogs should not be rejected solely for containing placeholder asset identifiers.
- allowed_behavior_change:
  - `tools/providers/project_generation_source_helpers.py`
  - `tools/providers/project_generation_validation.py`
  - `tests/test_project_generation_artifacts.py`
  - task/report/queue metadata files
- forbidden_goal_shift:
  - Do not add local project templates.
  - Do not create or rewrite generated business source as part of validation.
  - Do not weaken syntax/runtime failures broadly.

## Analysis / Find

- Latest run `20260503-174746-202806-orchestrate` produced `source_generation_report.json`.
- Retry worked: attempt 1 timed out, attempt 2 succeeded.
- `generic_validation` failed because startup/export probes could not import `vn` from a `src/` layout when launched from `scripts/`.
- Manual check with `PYTHONPATH=<project>/src` and `--headless` returned rc 0.
- `asset_placeholders.json` was flagged as generic placeholder content despite being a valid asset catalog concept.

## Plan

1. Add optional environment support to runtime command capture.
2. Set `PYTHONPATH` to project `src` for GUI/web entrypoint probes.
3. Retry GUI export with `--headless` only if the rich export command fails.
4. Avoid generic placeholder rejection for `asset_placeholders.json` when it only contains asset placeholder identifiers.
5. Add focused tests and run checks.

## Changes

- Runtime probes now run generated GUI/web entrypoints with project `src` on `PYTHONPATH`.
- GUI export probes retry plain `--headless` when richer export flags are rejected by the entrypoint.
- `asset_placeholders.json` no longer fails generic validation solely because it contains placeholder asset identifiers.
- Focused regressions were added for both behaviors.

## Acceptance

- [x] `python -m py_compile tools\providers\project_generation_source_helpers.py tools\providers\project_generation_validation.py tests\test_project_generation_artifacts.py`
- [x] `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_runtime_checks_support_src_layout_gui_entrypoint -v`
- [x] `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_generic_validation_allows_asset_placeholder_catalog_file -v`
- [x] `python scripts\workflow_checks.py`
- [x] `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`

## Integration Proof

- connected: generated project `src` layout connects to runtime probe environment.
- accumulated: runtime check records final command result after fallback.
- consumed: `generic_validation` consumes corrected probe results and avoids false placeholder hit.
