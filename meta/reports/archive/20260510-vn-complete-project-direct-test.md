# Demo Report - VN Complete Project Direct Generation Test

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `docs/12_virtual_team_contract.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `meta/backlog/execution_queue.json`

## Plan

1. Bind a Virtual Team Lane direct generation test.
2. Create a fresh complete VN project run.
3. Advance the run with bounded steps.
4. Inspect generated project status and probes.
5. Record first blocker or complete delivery evidence.
6. Run focused repo checks.

## Changes

- Created fresh run `D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510`.
- Advanced the run to source_generation.
- Did not manually edit generated project source.

## Verify

- PASS: `ctcp_orchestrate.py new-run --run-id vn-complete-project-direct-test-20260510 --goal <complete vn project goal>` returned 0.
- TIMEOUT: `ctcp_orchestrate.py advance --max-steps 20` exceeded 30 minutes.
- STATUS: fresh run reports `generic_validation.passed must be true`.
- FAIL: generated project unittest returned 1 on `SyntaxError` in `exporters/deliver.py`.
- FAIL: generated project `--help` and `--headless` probes returned 1 on the same `SyntaxError`.
- PASS: `module_protection_check.py --json` returned 0.
- PASS: `patch_check.py` returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption tests returned 0.
- PASS: `workflow_checks.py` returned 0.
- TIMEOUT: `verify_repo.ps1 -Profile code` exceeded 30 minutes during lite scenario replay; matching orphaned processes were stopped.

## Questions

- None.

## Demo

- Direct complete-project generation produced 47 files, a detected runnable entrypoint, README startup text, and product validation passed.
- It is not complete/deliverable yet: generic validation blocks because generated `exporters/deliver.py` has invalid Python syntax, plus visual/interaction evidence is still missing.

## First Failure And Repair

- first failure point evidence: `SyntaxError: closing parenthesis '}' does not match opening parenthesis '[' on line 98` in generated `exporters/deliver.py`.
- minimal fix strategy: repair CTCP/provider source_generation syntax/interface consistency in a separate scoped task; do not hand-edit the generated project source.

## Verify Failure Bundle

- command: `verify_repo.ps1 -Profile code`
- return code: timeout after 30 minutes.
- first failing/blocked gate: canonical verify did not return during `lite scenario replay`.
- evidence path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260511-002923`.
- minimal fix strategy: investigate SimLab replay duration separately before claiming full canonical verify pass.

## Skill Decision

- skill used: `ctcp-workflow`.
- skillized: no.
- persona_lab_impact: none.
