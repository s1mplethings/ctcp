# Task - VN Clean Run Source Retry Test

## Queue Binding

- Queue Item: `ADHOC-20260510-vn-clean-run-source-retry-test`
- Layer/Priority: `L1 / P0`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Scope

- Advance existing clean VN run: `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-clean-20260510`.
- Record fresh status and generated-project probes.
- Do not manually edit generated VN project source.

## Results

- `advance --max-steps 1` returned successfully.
- Run remains blocked at `artifacts/source_generation_report.json`.
- Current blocker remains `generic_validation.passed must be true`.
- Generated file count increased to 55, so provider/source_generation did retry and changed output.
- Current first runtime blocker:
  - `ImportError: cannot import name 'prompt_pipeline' from ...pipeline.prompt_pipeline`
- Current source_generation report summary:
  - missing symbols: `prompt_pipeline`, `Character`, `prompt_pipeline`
  - interface contract mismatches: 7
  - interface signature mismatches: 0
  - generated tests failed with rc=1
  - UX validation still lacks visual evidence files, preview source page, interaction controls, interaction trace, workspace snapshot, and export script.

## Command Evidence

- PASS: `ctcp_orchestrate.py advance --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-clean-20260510 --max-steps 1` returned 0.
- STATUS: `ctcp_orchestrate.py status` reports `generic_validation.passed must be true`.
- FAIL: generated project unittest returned 1 on missing `prompt_pipeline`.
- FAIL: generated project `--help` returned 1 on missing `prompt_pipeline`.
- FAIL: generated project `--headless` returned 1 on missing `prompt_pipeline`.
- PASS: `module_protection_check.py --json` returned 0.
- PASS: `patch_check.py` returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption tests returned 0.
- PASS: `workflow_checks.py` returned 0.
- TIMEOUT: `verify_repo.ps1 -Profile code` exceeded 30 minutes during lite scenario replay.
- CLEANUP: stopped matching orphaned `verify_repo.ps1` and `simlab\run.py --suite lite` processes.

## Failure Bundle Evidence

- first VN blocker: `generic_validation.passed=false`.
- first generated-project runtime error: missing `prompt_pipeline`.
- canonical verify blocker: timeout during lite scenario replay.
- evidence path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-230407`.
- minimal next repair: fix CTCP/provider source_generation cross-file interface consistency in a separate scoped task.
