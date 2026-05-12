# Task - VN Complete Project Direct Generation Test

## Queue Binding

- Queue Item: `ADHOC-20260510-vn-complete-project-direct-test`
- Layer/Priority: `L1 / P0`
- Lane: `Virtual Team Lane`
- [x] Code changes allowed

## Scope

- Create and advance fresh complete VN project generation run:
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510`
- Do not manually edit generated project source.
- Judge result by generated project status, validation reports, and probes.

## Results

- Fresh run created and advanced to source_generation.
- `advance --max-steps 20` exceeded 30 minutes, but source_generation report exists.
- Run status is blocked at `artifacts/source_generation_report.json`.
- Reason: `generic_validation.passed must be true`.
- Generated evidence:
  - 47 files.
  - runnable entrypoint detected.
  - README startup text detected.
  - product validation passed.
  - generic validation failed.
- First runtime blocker:
  - generated `exporters/deliver.py` has `SyntaxError: closing parenthesis '}' does not match opening parenthesis '[' on line 98`.
  - generated unittest, `--help`, and `--headless` probes fail on that syntax error.
- Additional blockers:
  - interface contract mismatches: 2.
  - interface signature mismatches: 1.
  - visual/interaction evidence is missing preview source, controls, interaction trace, workspace snapshot, and export script.

## Command Evidence

- PASS: `ctcp_orchestrate.py new-run --run-id vn-complete-project-direct-test-20260510 --goal <complete vn project goal>` returned 0.
- TIMEOUT: `ctcp_orchestrate.py advance --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510 --max-steps 20` exceeded 30 minutes.
- STATUS: `ctcp_orchestrate.py status` reports `generic_validation.passed must be true`.
- FAIL: generated project unittest returned 1 on `SyntaxError` in `exporters/deliver.py`.
- FAIL: generated project `--help` returned 1 on the same syntax error.
- FAIL: generated project `--headless` returned 1 on the same syntax error.
- PASS: `module_protection_check.py --json` returned 0.
- PASS: `patch_check.py` returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption tests returned 0.
- PASS: `workflow_checks.py` returned 0.
- TIMEOUT: `verify_repo.ps1 -Profile code` exceeded 30 minutes during lite scenario replay.
- CLEANUP: stopped matching orphaned `verify_repo.ps1` and `simlab\run.py --suite lite` processes.

## Failure Bundle Evidence

- first project-generation blocker: `generic_validation.passed=false`.
- first generated-project runtime error: `SyntaxError` in generated `exporters/deliver.py`.
- canonical verify blocker: timeout during lite scenario replay.
- evidence path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260511-002923`.
- minimal next repair: fix CTCP/provider source_generation syntax and cross-file interface consistency in a separate scoped task.
