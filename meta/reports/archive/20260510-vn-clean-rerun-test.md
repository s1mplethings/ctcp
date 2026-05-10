# Demo Report - VN Clean Rerun Test

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `meta/backlog/execution_queue.json`
- `meta/run_pointers/LAST_RUN.txt`
- `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer*`

## Plan

1. Bind a separate cleanup/retest task.
2. Delete only external VN generation run directories matching the customer VN prefix after path-boundary checks.
3. Clear or update stale run pointers.
4. Create and advance a fresh VN run.
5. Record fresh-run status, first blocker or generated evidence, and verification results.

## Changes

- Deleted the old external VN run directories:
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510`
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b`
- Created fresh run `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-clean-20260510`.
- `LAST_RUN.txt` now points at the fresh run.
- Did not delete Git history, task/report archives, credentials, or manually edit generated VN source.

## Verify

- PASS: old external VN run directories were deleted after path-boundary checks.
- PASS: fresh run was created.
- TIMEOUT: `ctcp_orchestrate.py advance --max-steps 20` exceeded 30 minutes.
- STATUS: fresh run reports blocked at `artifacts/source_generation_report.json` because `generic_validation.passed must be true`.
- FAIL: generated project unittest returned 1 because `export_project_assets` is imported but not defined by `exporters/deliver.py`.
- FAIL: generated project `--help` and `--headless` probes return 1 on the same import error.
- PASS: `module_protection_check.py --json` returned 0.
- PASS: `patch_check.py` returned 0.
- PASS: `code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption tests returned 0.
- PASS: `workflow_checks.py` returned 0 after evidence sections were added.
- TIMEOUT: `verify_repo.ps1 -Profile code` exceeded 30 minutes during lite scenario replay; matching orphaned processes were stopped.

## Questions

- None.

## Demo

- Clean rerun generated a VN project with 45 files, a detected entrypoint, README startup text, story/data files, background/sprite planning files, and tests.
- It is not deliverable yet: source_generation remains blocked by generated-source import/interface mismatch and missing GUI/visual interaction evidence.

## First Failure And Repair

- first failure point evidence: fresh run status says `generic_validation.passed must be true`; generated self-test fails importing `export_project_assets` from `exporters/deliver.py`.
- minimal fix strategy: keep generated VN source untouched and repair CTCP/provider source_generation behavior in a separate scoped task so future provider output aligns exported symbols, tests, entrypoints, and visual interaction evidence.

## Verify Failure Bundle

- command: `verify_repo.ps1 -Profile code`
- return code: timeout after 30 minutes.
- first failing/blocked gate: canonical verify did not return during `lite scenario replay`.
- evidence path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-220118`.
- minimal fix strategy: investigate SimLab replay duration separately before claiming full canonical verify pass.

## Skill Decision

- skill used: `ctcp-workflow`.
- skillized: no.
- persona_lab_impact: none.
