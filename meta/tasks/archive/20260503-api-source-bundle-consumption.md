# Task Archive - API Source Bundle Consumption

- Date: `2026-05-03`
- Queue Item: `ADHOC-20260503-api-source-bundle-consumption`
- Lane: Delivery Lane
- Status: done

## Scope

Fix the API source-generation path so a real API response can provide concrete generated project source files, without restoring deterministic local project templates.

## Changes

- Added `ctcp_adapters/source_generation_prompt.py` for source-generation file bundle prompt requirements.
- Wired `ctcp_adapters/ctcp_artifact_normalizers.py` to include those requirements for `chair/source_generation`.
- Updated `tools/providers/project_generation_source_stage.py` to consume provider-authored `path/content` rows and write them under `project_root`.
- Updated `tools/providers/project_generation_provenance.py` to report `provider_authored_source`.
- Added focused regressions in `tests/test_project_generation_provenance.py` and `tests/test_api_agent_templates.py`.

## Verification

- `python -m py_compile ...` passed.
- `python tests\test_project_generation_provenance.py` passed (`3` tests).
- `python tests\test_api_agent_templates.py -k test_render_prompt_for_source_generation_requests_file_content_bundle -v` passed (`1` test).
- `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py` passed (`36` tests).
- `python scripts\workflow_checks.py` passed.
- `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- `module_protection_check` and `verify_repo -Profile code` are blocked by unrelated existing dirty lane files outside this task write scope.

## Result

The source-generation API now has a concrete source-file contract, and production source generation writes provider-authored files when the API returns them. Generic prose-only API output still does not pass as generated source.
