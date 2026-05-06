# Task Archive - Remove Production Local Project Templates

## Queue Binding

- Queue Item: `ADHOC-20260503-remove-production-local-project-templates`
- Date Closed: `2026-05-03`
- Lane: Delivery Lane
- Status: done

## Scope

- Production project generation must not create business source files from deterministic local templates/materializers.
- If provider-authored source files are absent, source generation must block before local template files are produced.
- Historical benchmark/scaffold assets remain out of scope for this task.

## Changes

- Removed production source-stage dependency on `materialize_business_files()`.
- Added explicit blocked source-generation report for disabled production local templates.
- Added provenance/completion fields for `disabled_local_templates` and `local_templates_disabled`.
- Updated project-generation artifact, provenance, benchmark, and variant regressions.
- Updated quality gate docs and issue memory.

## Verify

- `python -m py_compile tools\providers\project_generation_source_stage.py tools\providers\project_generation_provenance.py tests\test_plane_lite_benchmark_regression.py tests\test_project_generation_variant_content.py` passed.
- `python tests\test_plane_lite_benchmark_regression.py -k test_high_quality_source_generation_writes_extended_coverage` passed.
- `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_variant_content.py` passed.
- `python tests\test_project_generation_provenance.py` passed.
- `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py` passed.
- `python scripts\module_protection_check.py` passed.
- `python scripts\workflow_checks.py` passed.
- `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` passed.

## Evidence

- Production local template/materializer call is unreachable from production source generation.
- Regression coverage proves no local business template files are emitted for production provider-source absence.
- Canonical code-profile verify passed with `480` Python unit tests and `4` skips.
