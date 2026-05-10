# Task - VN Clean Rerun Test

## Queue Binding

- Queue Item: `ADHOC-20260510-vn-clean-rerun-test`
- Layer/Priority: `L1 / P0`
- Lane: `Delivery Lane`
- [x] Code changes allowed
- External run cleanup allowed: `true`

## Scope

- Delete external VN generation run directories under `D:\.c_projects\adc\ctcp_runs\ctcp` whose names start with `vn-project-generation-customer`.
- Create and advance a fresh CTCP VN run.
- Do not delete Git history, repository task/report archives, provider credentials, or manually edit generated VN project source.

## Results

- Deleted:
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510`
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b`
- Created:
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-clean-20260510`
- `meta/run_pointers/LAST_RUN.txt` points at the fresh run.
- Fresh run advanced through analysis, planning, contract review, output contract freeze, and source_generation.
- Fresh run remains blocked at `artifacts/source_generation_report.json` because `generic_validation.passed` is false.
- Generated project evidence:
  - 45 files generated.
  - runnable entrypoint and README startup detected.
  - generated unittest, `--help`, and `--headless` probes fail because `export_project_assets` is imported but not defined by `exporters/deliver.py`.
  - visual/interaction evidence is still missing preview source, controls, interaction trace, workspace snapshot, and export script.
- No generated VN source was manually patched.

## Command Evidence

- PASS: queue JSON parse returned `queue json ok`.
- PASS: path-boundary checks accepted only matching VN customer run directories under `D:\.c_projects\adc\ctcp_runs\ctcp`.
- PASS: `ctcp_orchestrate.py new-run --run-id vn-project-generation-customer-clean-20260510 --goal <vn customer goal>` returned 0.
- TIMEOUT: `ctcp_orchestrate.py advance --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-clean-20260510 --max-steps 20` exceeded 30 minutes.
- STATUS: `ctcp_orchestrate.py status` reports `generic_validation.passed must be true`.
- FAIL: generated project unittest returned 1 on missing `export_project_assets`.
- FAIL: generated project `--help` and `--headless` returned 1 on the same import error.
- PASS: `module_protection_check.py --json` returned 0.
- PASS: `patch_check.py` returned 0.
- PASS: `code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption tests returned 0.
- PASS: `workflow_checks.py` returned 0 after required evidence sections were added.
- TIMEOUT: `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` exceeded 30 minutes during lite scenario replay.
- CLEANUP: stopped matching orphaned `verify_repo.ps1` and `simlab\run.py --suite lite` processes.
- Latest incomplete replay: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-220118`.

## Failure Bundle Evidence

- first VN run blocker: fresh source_generation report remains blocked by `generic_validation.passed=false`.
- first generated-project runtime error: `ImportError: cannot import name 'export_project_assets'`.
- canonical verify blocker: timeout during lite scenario replay.
- minimal next repair: fix CTCP/provider source_generation behavior in a separate scoped task; do not hand-edit generated VN source.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: CTCP queue discipline and orchestrator run workflow were required.
