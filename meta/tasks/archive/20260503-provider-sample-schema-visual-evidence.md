# Task Archive - Provider Sample Schema And Headless Visual Evidence

## Queue Binding

- Queue Item: `ADHOC-20260503-provider-sample-schema-visual-evidence`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: latest VN run generated provider-authored source and runtime probes now pass, but source generation remained blocked because domain sample validation only read the old flat sample schema and visual evidence capture ignored files emitted by `--headless` fallback into the generated scripts directory.
- Lane: Delivery Lane.
- Scope boundary: provider-authored sample schema compatibility and headless fallback export evidence only; no local business source generation.

## Analysis / Find

- Latest run `20260503-193149-962580-orchestrate` produced provider-authored source.
- `generic_validation.passed` was true and startup/export probes passed.
- `domain_validation.passed` was false because validator reported `scene_count=0`, `branch_point_count=0`, and `valid_character_cards=0` while the sample had nested `chapters[].scenes[]`, branch lists, and character descriptions/sprites.
- `gate_layers.result.passed` was false because the successful `--headless` fallback wrote `exported_project_summary.json` into `scripts/`, while visual evidence scanned only the temporary `--out` directory.

## Plan

1. Extract narrative sample metrics into a small helper module.
2. Support nested `chapters[].scenes[]`, `branches`, `bg/sfx/cg`, and `id/description/sprites` style sample records.
3. Reuse the same metric helper in source-stage sample quality.
4. Copy headless fallback export files into the visual evidence export directory when the entrypoint does not support `--out`.
5. Add focused tests and run checks.

## Changes

- Added `tools/providers/project_generation_sample_metrics.py`.
- `tools/providers/project_generation_validation.py` now uses shared narrative sample metrics.
- `tools/providers/project_generation_source_stage.py` now uses the same metrics for sample quality.
- `tools/providers/project_generation_source_helpers.py` now copies successful GUI `--headless` fallback outputs into the visual evidence export directory.
- `tests/test_project_generation_artifacts.py` covers nested provider sample metrics and headless fallback visual evidence.

## Acceptance

- [x] `python -m py_compile tools\providers\project_generation_source_helpers.py tools\providers\project_generation_sample_metrics.py tools\providers\project_generation_source_stage.py tools\providers\project_generation_validation.py tests\test_project_generation_artifacts.py`
- [x] `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_narrative_sample_metrics_accept_provider_nested_schema -v`
- [x] `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_runtime_checks_support_src_layout_gui_entrypoint -v`
- [x] live-run recheck against `20260503-193149-962580-orchestrate`: updated domain validation passed with `scene_count=8`, `branch_point_count=2`, `valid_character_cards=3`; runtime visual evidence returned `visual_status=provided`, `visual_type=real_export_page`, and `gate_result.passed=true`.
- [x] `python scripts\workflow_checks.py`
- [x] `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
- [ ] full canonical verify: blocked by pre-existing out-of-scope dirty support-lane files.

## Integration Proof

- connected: provider-authored nested sample schema connects to shared narrative metrics.
- accumulated: successful `--headless` fallback export files are accumulated into visual evidence inputs.
- consumed: source generation domain/result gates consume the corrected metrics and evidence path.
