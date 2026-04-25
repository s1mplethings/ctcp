# Task - Plane Lite Team PM benchmark test

## Queue Binding

- Queue Item: `ADHOC-20260421-plane-lite-team-pm-benchmark`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user provided `plane_lite_team_pm_test_pack.zip` and requested a real benchmark execution against CTCP, not a static review.
- Dependency check:
  - `ADHOC-20260421-default-mainline-freeze = done`
- Lane: Delivery Lane for this repository task because the requested work is a bounded benchmark execution/evaluation. The tested generated-project flow itself is expected to route as Virtual Team Lane because the benchmark asks for a new Plane-lite/Focalboard-lite product.
- Scope boundary: use only the unpacked benchmark markdown files and `benchmark_case.json` as the project-test source of truth. Do not alter the benchmark, change the project topic, or broaden the requested MVP scope.

## Task Truth Source (single source for current task)

- task_purpose:
  - unpack and fully read the benchmark zip
  - drive CTCP through the benchmark scripted turns as a real project-generation test
  - collect intermediate progress, step acceptance, verify, screenshot/README/startup/package, and final acceptance-bundle evidence
  - judge whether the output genuinely matches a Plane-lite / Focalboard-lite small-team task collaboration platform
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/`
  - `meta/reports/`
  - `meta/tasks/`
  - external benchmark input/execution/evidence directories outside the repository
- forbidden_goal_shift:
  - do not make the benchmark easier
  - do not change the project to another topic
  - do not treat final code generation alone as success
  - do not hide missing step acceptance or delivery evidence
- in_scope_modules:
  - benchmark unpack/read/evaluation
  - CTCP external run execution
  - generated project artifact inspection
  - report and archive metadata
- out_of_scope_modules:
  - production CTCP runtime implementation changes
  - benchmark content edits
  - repo-local generated project output
  - unrelated cleanup of the existing dirty worktree
- completion_evidence:
  - unpacked benchmark readlist and source-of-truth summary
  - scripted-turn transcript or equivalent command/event evidence
  - generated run artifacts, if CTCP can produce them
  - acceptance bundle review with first failure point and final PASS/PARTIAL/FAIL conclusion

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/`
  - `meta/reports/`
  - `meta/tasks/`
  - external directories under `D:\.c_projects\adc\ctcp_benchmark_runs\plane-lite-team-pm-20260421\`
- Protected Paths:
  - benchmark zip contents except unpacking to a read-only input folder
  - CTCP runtime/source/docs/tests
  - generated project output except runtime execution artifacts in the external run directory
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `N/A - benchmark execution/report task only; no frozen-kernel runtime changes are authorized`
- Forbidden Bypass:
  - do not skip benchmark file reading before running turns
  - do not claim pass without checking intermediate evidence and delivery bundle contents
  - do not count a process bundle as final user-facing project delivery if the benchmark expects runnable product evidence
- Acceptance Checks:
  - benchmark zip unpacked outside repo
  - every unpacked benchmark markdown file and `benchmark_case.json` read
  - scripted turns executed or first runtime blocker recorded
  - final generated artifact/bundle inspected against benchmark must-have/forbidden scope
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`

## Analysis / Find (before plan)

- Entrypoint analysis: bounded Delivery Lane benchmark execution; CTCP project-generation path under test should exercise Virtual Team Lane semantics for a new project.
- Source of truth:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - unpacked benchmark markdown files
  - unpacked `benchmark_case.json`
- Current break point / missing wiring:
  - unknown until benchmark read and scripted execution complete
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: user-provided benchmark zip and CTCP canonical orchestration/support/project-generation entrypoints.
- current_module: benchmark execution and evidence report.
- downstream: generated project inspection and final benchmark result.
- source_of_truth: benchmark files only for the project request; CTCP contracts only for how this repo task is executed and reported.
- fallback: if a scripted turn blocks, record the first real blocker, apply only minimal benchmark-preserving clarification or repair if available, then continue the smallest viable execution path.
- acceptance_test:
  - benchmark file read evidence
  - external run artifacts and transcript evidence
  - generated project verify/screenshot/package evidence where available
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`
- forbidden_bypass:
  - no static-only review
  - no topic substitution
  - no final-pass claim without step/gate/delivery evidence
- user_visible_effect:
  - a reviewable benchmark result that identifies the first real failure point and next repair.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Benchmark zip is unpacked outside the repo, all benchmark markdown files plus `benchmark_case.json` are read, and the project target/must-have/forbidden/persona/scripted-turn summary is recorded.
- [x] DoD-2: Scripted turns are executed through CTCP as realistically as possible, with turn input/output and intermediate progress/step acceptance/gate evidence collected.
- [x] DoD-3: Final generated artifacts are inspected for runnable Plane-lite/Focalboard-lite fit, verify evidence, screenshot/README/startup/package, final bundle, first failure point, and PASS/PARTIAL/FAIL conclusion.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A - benchmark and repo-local artifacts sufficient`
- [x] Code changes allowed
- [x] Patch applies cleanly via repo-local file edits in allowed write scope
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Unpack the benchmark zip to an external run/input directory and list all files.
2. Read every benchmark markdown file and `benchmark_case.json`; summarize source-of-truth constraints.
3. Execute the scripted turns through CTCP with the narrowest canonical entrypoint that produces real run artifacts.
4. Inspect run artifacts for intermediate progress, step acceptance, gate/verify evidence, generated project files, screenshot/README/startup steps/package, and acceptance bundle.
5. If a runtime blocker appears, identify the first real failure point and continue with the smallest viable benchmark-preserving test path.
6. Run repo workflow checks and canonical doc-only verify for the metadata/report patch.
7. Update `meta/reports/LAST.md`, archive records, and final user-facing benchmark result.

## Notes / Decisions

- Check/Contrast/Fix evidence: compare benchmark source-of-truth requirements against actual run artifacts at planning, implementation, verification, delivery, and bundle-review stages; repair only metadata/report gaps within this task unless the benchmark run itself provides a minimal safe continuation path.
- completion criteria evidence: complete only after benchmark read evidence, scripted-turn evidence or first-blocker evidence, artifact inspection, and final report are recorded; connected + accumulated + consumed was checked for support entry -> run artifacts -> report consumption, and failed at project-generation output consumption.
- Issue memory decision: no issue memory entry yet; if the benchmark exposes a recurring/user-visible CTCP failure class, record the candidate in the final report and decide whether a later repair task should update issue memory with regression coverage.
- Skill decision (`skillized: no, because ...`): `skillized: no, because this is a one-off benchmark execution/evaluation using existing ctcp-workflow and ctcp-run-report skills; a reusable benchmark harness skill would only be justified after repeated runs with stable inputs and scoring.`
- persona_lab_impact: benchmark uses a customer persona and scripted turns for generated-project acceptance, but does not modify production persona/runtime behavior.

## Results

- Benchmark input:
  - zip: `D:\.c_projects\adc\ctcp\plane_lite_team_pm_test_pack.zip`
  - unpacked input: `D:\.c_projects\adc\ctcp_benchmark_runs\plane-lite-team-pm-20260421\input\plane_lite_team_pm_test_pack\`
- Execution evidence:
  - first failed command in requested repo root: `python scripts/ctcp_orchestrate.py --help` => exit `1`, `ModuleNotFoundError: No module named 'ctcp_adapters'`
  - clean continuation workspace: `D:\.c_projects\cqa`, commit `50b1dca8a790d80a89b386ee2283f1f1670cb4f0`
  - scripted support transcript: `D:\.c_projects\adc\ctcp_benchmark_runs\plane-lite-team-pm-20260421\evidence\scripted_turn_transcript_utf8.json`
  - scripted run: `D:\.c_projects\adc\ctcp_benchmark_runs\plane-lite-team-pm-20260421\runs_utf8\cqa\20260421-213157-748252-orchestrate`
  - control run: `D:\.c_projects\adc\ctcp_benchmark_runs\plane-lite-team-pm-20260421\runs_control\cqa\20260421-214012-763617-orchestrate`
  - acceptance bundle: `D:\.c_projects\adc\ctcp_benchmark_runs\plane-lite-team-pm-20260421\evidence\plane_lite_team_pm_benchmark_acceptance_bundle.zip`
- Benchmark result:
  - Verdict: `FAIL`
  - The scripted run did not generate a Plane-lite/Focalboard-lite project.
  - The run selected `wf_orchestrator_only`, recorded `project_generation_goal=false`, and blocked at PatchMaker with missing `artifacts/diff.patch`.
  - No runnable project, verify report, README/startup steps, screenshot, final project package, or generated-project acceptance bundle exists.
- Verification summary:
  - `python scripts/workflow_checks.py` initially failed on missing `completion criteria evidence` marker; after metadata fix, exit `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only` => exit `1`
  - first verify failure: `module protection check` because the shared worktree already contains many dirty files outside this task's allowed write scope, including frozen-kernel paths such as `AGENTS.md`, `docs/04_execution_flow.md`, `scripts/ctcp_orchestrate.py`, and `scripts/verify_repo.ps1`
  - minimal fix strategy: isolate or close unrelated dirty/frozen-kernel work before canonical verify for this metadata task; do not expand this benchmark task's write scope to cover unrelated existing changes
