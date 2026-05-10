# Demo Report - VN Clean Run Source Retry Test

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `meta/backlog/execution_queue.json`
- `meta/run_pointers/LAST_RUN.txt`
- `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-clean-20260510`

## Plan

1. Bind a narrow retest task.
2. Advance the existing clean VN run once.
3. Inspect status and generated-project probes.
4. Record first blocker or pass evidence.
5. Run focused repo checks.

## Changes

- Advanced the existing clean VN run once with `--max-steps 1`.
- Did not manually edit generated VN project source.

## Verify

- PASS: `ctcp_orchestrate.py advance --max-steps 1` returned 0.
- STATUS: fresh status still reports `generic_validation.passed must be true`.
- FAIL: generated project unittest returned 1 because `service.py` imports `prompt_pipeline` from `pipeline/prompt_pipeline.py`, but that symbol is not defined.
- FAIL: generated project `--help` and `--headless` probes returned 1 on the same missing `prompt_pipeline` import.
- PASS: `module_protection_check.py --json` returned 0.
- PASS: `patch_check.py` returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption tests returned 0.
- PASS: `workflow_checks.py` returned 0.
- TIMEOUT: `verify_repo.ps1 -Profile code` exceeded 30 minutes during lite scenario replay; matching orphaned processes were stopped.

## Questions

- None.

## Demo

- Retest did run and changed provider output: generated files increased to 55.
- The project is still not deliverable. The current first runtime blocker is missing `prompt_pipeline`; UX/visual interaction evidence is also still missing.

## First Failure And Repair

- first failure point evidence: `generic_validation.passed=false`; generated tests and entrypoint probes fail on `ImportError: cannot import name 'prompt_pipeline'`.
- minimal fix strategy: fix CTCP/provider source_generation interface consistency in a separate scoped task; do not hand-edit this generated VN source.

## Verify Failure Bundle

- command: `verify_repo.ps1 -Profile code`
- return code: timeout after 30 minutes.
- first failing/blocked gate: canonical verify did not return during `lite scenario replay`.
- evidence path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-230407`.
- minimal fix strategy: investigate SimLab replay duration separately before claiming full canonical verify pass.

## Skill Decision

- skill used: `ctcp-workflow`.
- skillized: no.
- persona_lab_impact: none.
