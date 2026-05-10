# Task - VN Complete Project Direct Generation Test

## Queue Binding

- Queue Item: `ADHOC-20260510-vn-complete-project-direct-test`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Virtual Team Lane`
- [x] Code changes allowed

## Context

- User request: directly test generating a complete project.
- Direct test run id: `vn-complete-project-direct-test-20260510`.
- Goal shape: complete runnable VN project with story, background plan/assets, character sprites, preview/export path, interaction evidence, README, tests, and delivery evidence.
- Boundary: CTCP/provider must generate the project; Codex must not hand-author generated project source.

## Task Truth Source

- task_purpose:
  - Run a fresh end-to-end complete VN project generation test and report whether CTCP can deliver a complete runnable project.
- allowed_behavior_change:
  - create and advance a fresh external run.
  - update task/report/archive metadata.
- forbidden_goal_shift:
  - Do not manually edit generated VN project source.
  - Do not weaken validation gates.
  - Do not treat partial artifacts as complete delivery.
- in_scope_modules:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260510-vn-complete-project-direct-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260510-vn-complete-project-direct-test.md`
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510`
- out_of_scope_modules:
  - generated project manual source edits
  - provider credentials
  - frozen kernels
  - unrelated external runs
- completion_evidence:
  - fresh run creation result recorded.
  - Virtual Team/plan artifacts recorded or first missing artifact recorded.
  - source_generation/project delivery status recorded.
  - generated project probes recorded if project files exist.
  - focused repo gate results recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260510-vn-complete-project-direct-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260510-vn-complete-project-direct-test.md`
  - `D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510`
- Protected Paths:
  - `.git`
  - generated project manual source edits
  - provider credentials
  - frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no generated-source manual patching.
  - no gate weakening.
  - no partial-output success claim.
- Acceptance Checks:
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id vn-complete-project-direct-test-20260510 --goal <complete vn project goal>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510 --max-steps 20`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510`
  - generated project unittest/probes if source files exist.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`

## Analysis / Find

- The previous clean VN run proved CTCP can reach source_generation and generate many files, but it still failed cross-file interface validation.
- This task tests a fresh complete-project goal directly, so the result should be judged by fresh run evidence, not by old run assumptions.
- Because this is a new project request, it is routed as Virtual Team Lane; implementation is only valid after the run produces planning/design artifacts.

## Plan

1. Bind this Virtual Team Lane direct generation test.
2. Create a fresh external run for the complete VN project goal.
3. Advance the run with bounded steps.
4. Inspect run status, source_generation/project_manifest evidence, generated files, and runnable probes.
5. Record first blocker or complete delivery evidence.
6. Run focused repo gates and archive this task/report.

## Integration Check

- upstream: user asked to directly test complete project generation.
- current_module: CTCP orchestrator new-run/advance over a fresh VN project run.
- downstream: generated project source, validation reports, delivery status, and user-visible evidence.
- source_of_truth: `D:\.c_projects\adc\ctcp_runs\ctcp\vn-complete-project-direct-test-20260510`.
- fallback: if generation blocks, record the first blocker and stop without generated-source patching.
- acceptance_test: orchestrator status plus generated project probes where available.
- forbidden_bypass: no manual generated-source repair and no partial-output success claim.
- user_visible_effect: the user sees whether CTCP can directly generate a complete runnable VN project or where it currently fails.

## Acceptance

- [x] Lane selected as Virtual Team Lane.
- [x] Queue item bound before run creation.
- [ ] Fresh run created.
- [ ] Fresh run advanced or timeout recorded.
- [ ] Generated project status/probes recorded.
- [ ] Repo focused gates recorded.

## Check/Contrast/Fix Loop Evidence

- check: pending.
- contrast: pending.
- fix: pending.
- re-check: pending.

## Completion Criteria Evidence

- completion criteria evidence: pending.

## Issue Memory Decision Evidence

- issue memory decision evidence: pending.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: the task requires CTCP queue discipline, Virtual Team Lane routing, external run orchestration, and gate reporting.
- skillized: no.
- persona_lab_impact: none.
