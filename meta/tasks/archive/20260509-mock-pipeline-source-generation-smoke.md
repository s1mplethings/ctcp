# Task Archive - Mock Pipeline Source Generation Smoke

## Queue Binding

- Queue Item: `ADHOC-20260509-mock-pipeline-source-generation-smoke`
- Layer/Priority: `L1 / P0`
- Lane: `Delivery Lane`
- Date: `2026-05-09`

## Scope

- Make the local `mock_agent` pipeline smoke exercise the provider-authored source-file path expected from real source_generation agents.
- Preserve the production rule that local deterministic templates are disabled for final source generation.
- Improve blocked source_generation reports so gates receive explicit failed `generic_validation` shape.

## Changes

- Updated `tools/providers/mock_agent.py` so `chair/source_generation` emits a compact provider source bundle and then calls the existing `normalize_source_generation` path.
- Updated `tools/providers/project_generation_source_stage.py` so blocked source_generation reports include an explicit failed `generic_validation` object.
- Added `tests/test_mock_agent_pipeline.py::test_mock_source_generation_emits_provider_authored_project`.
- Hardened mock pipeline tests against ambient `CTCP_FORCE_PROVIDER=api_agent`.

## Command Evidence

- PASS: `.venv\Scripts\python.exe -m py_compile tools\providers\mock_agent.py tools\providers\project_generation_source_stage.py tests\test_mock_agent_pipeline.py` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v` returned 1 because ambient `CTCP_FORCE_PROVIDER=api_agent` overrode the mock dispatch config.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v` returned 0, 5 tests OK after clearing provider override env in the test stub.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_provenance.py" -v` returned 0, 4 tests OK.
- PASS: fresh run `D:\.c_projects\adc\ctcp_runs\ctcp\agent-exchange-mock-project-pipeline-fixed-20260509` returned `PASS: verify succeeded`.
- PASS: status for that run reported `run_status=pass`, `iterations=1/3`, and `reason=run already pass`.
- FIRST FAILURE: canonical verify first failed at lite scenario replay because default `D:\ctcp_runs` was not writable.
- PASS: canonical verify passed after setting `CTCP_RUNS_ROOT=D:\.c_projects\adc\ctcp_runs`; 532 Python tests OK with 4 skipped.

## Pipeline Evidence

- Provider ledger: `row_count=13`, `critical_step_count=12`, `critical_api_step_count=0`, `fallback_count=0`, `failed_count=0`.
- Source generation: `status=pass`, `generic_validation.passed=true`, all source gate layers passed, and `source_customization_completion.final_delivery_allowed=true`.
- Delivery verify: `artifacts/verify_report.json` has `result=PASS`, `gate=lite`, and no failures.

## Merge Decision

- experiment_result: successful.
- merge_decision: merged into the local mock-provider mainline.
- reason: fresh external pipeline run reached PASS with no external API usage and no local-template fallback.
