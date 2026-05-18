# Task - Non-Web Project Matrix And Attribution Review Pack

## Queue Binding

- Queue Item: `ADHOC-20260514-non-web-project-matrix-attribution-review-pack`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: enter CTCP Phase 15 and expand ordinary concrete generation beyond Web/API/full-stack projects.
- Existing ordinary concrete generation already passes for issue tracker, todo, notes, auth, task board, and Kanban.
- This task must add non-web project categories and explicit generation attribution/review evidence.

## Task Truth Source

- task_purpose:
  - Add Non-Web Project Type Matrix with CSV analyzer CLI, log analyzer CLI, text utils package, and terminal quiz game.
  - Add `generation_attribution.json` evidence for ordinary concrete benchmarks.
  - Add concise review pack artifacts for human/ChatGPT review.
- required_runtime_chain:
  - `new-run -> status -> advance -> analysis -> source_generation -> project_output -> generated tests -> CLI/package validation`.
- allowed_behavior_change:
  - Add bounded non-web concrete fast paths with provenance and attribution.
  - Extend fast path registry/materializer dispatch for non-web projects.
  - Extend benchmark reports/summaries with Attribution sections.
  - Add `meta/reports/REVIEW_PACK.md`.
- completion_evidence:
  - Non-web matrix reports `4/4` passed.
  - Existing full-stack, concrete matrix, concrete issue tracker, and agent benchmarks remain passed.
  - `generation_attribution.json` exists and clearly states no agent-project/scaffold/local-agent-runtime use for ordinary concrete runs.
  - Full unittest discover, script gates, and canonical repo verify pass.
- forbidden_goal_shift:
  - Do not use `agent-manifest`, `agent-scaffold`, or `agent-project` as a substitute.
  - Do not mock CLI/file/test success.
  - Do not weaken fixtures or skip analysis/source_generation.
  - Do not delete existing concrete or agent benchmarks.
  - Do not rewrite orchestrator or migrate unrelated modules.
- in_scope_modules:
  - ordinary project generation fast path registry/materializers.
  - non-web concrete benchmark runner, fixtures, validators, and focused tests.
  - generation attribution/report/review-pack evidence.
- out_of_scope_modules:
  - agent runtime/planner/web tool implementation.
  - provider credentials or real external API clients.
  - broad orchestrator rewrites and unrelated frozen kernels.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_fast_path_registry.py`
  - `tools/providers/project_generation_fast_path_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_attribution.py`
  - `tools/providers/project_generation_non_web_fast_paths.py`
  - `tests/non_web_project_matrix/`
  - `tests/test_non_web_project_matrix.py`
  - `tests/test_csv_expense_analyzer_generation.py`
  - `tests/test_log_analyzer_generation.py`
  - `tests/test_text_utils_package_generation.py`
  - `tests/test_terminal_quiz_game_generation.py`
  - `tests/test_generation_attribution_report.py`
  - `tests/test_review_pack_generation.py`
  - `tests/test_kanban_app_generation.py`
  - `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
  - `tests/concrete_project_matrix/run_matrix_benchmark.py`
  - `tests/full_stack_app_benchmark/run_full_stack_benchmark.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/reports/REVIEW_PACK.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-non-web-project-matrix-attribution-review-pack.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-non-web-project-matrix-attribution-review-pack.md`
- Protected Paths:
  - `.git`
  - agent runtime/planner/web implementation files unless benchmark output changes during regression
  - benchmark fixture lowering
  - provider credentials
  - real external API clients
  - unrelated frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no agent-project substitution
  - no fake CLI/file/test success
  - no benchmark fixture weakening
  - no source_generation skip
  - no benchmark runner hardcoded pass
  - no broad orchestrator rewrite
- Acceptance Checks:
  - non-web matrix 4/4 pass
  - generated CLI/package/game tests pass
  - attribution artifacts record no agent-project/scaffold/local-agent-runtime use
  - existing concrete/full-stack/agent benchmarks remain pass
  - canonical repo verification pass

## Analysis / Find

- Current concrete coverage is backend/full-stack heavy; non-web CLI/package/game categories need ordinary generation proof.
- Attribution must distinguish ordinary mainline, local materializer use, provider authorship, and absence of agent-project/scaffold/runtime.
- The implementation should stay local: new non-web fast path file, attribution writer, registry/materializer extension, benchmark runners, docs, and tests.

## Plan

1. Add attribution writer and wire source_generation to emit `artifacts/generation_attribution.json`.
2. Add non-web fast path detection/defaults/templates/materializer for four project categories.
3. Add non-web matrix fixtures, runner, validators, generated summaries, and report Attribution sections.
4. Extend existing concrete/full-stack benchmark summaries and reports with attribution.
5. Add focused tests and docs/review pack, then run required benchmark/regression/verify commands.

## Acceptance Checks

- [x] non-web matrix runs all 4 fixtures.
- [x] CSV Expense Analyzer CLI benchmark passes.
- [x] Log Analyzer CLI benchmark passes.
- [x] Text Utilities Package benchmark passes.
- [x] Terminal Quiz Game benchmark passes.
- [x] all non-web generated tests pass.
- [x] ordinary `new-run/status/advance` mainline is preserved.
- [x] no agent-project/scaffold/local agent runtime is used for ordinary concrete runs.
- [x] `generation_attribution.json` exists and is included in benchmark summaries.
- [x] attribution records local materializer/provider authorship accurately.
- [x] existing full-stack, concrete matrix, and concrete benchmark remain pass.
- [x] agent planner/runtime/factory benchmarks remain pass.
- [x] review pack exists and includes summary, risks, artifacts, and commands.
- [x] unittest discover passes.
- [x] repo verification passes.

## Integration Check

- upstream: ordinary concrete project-generation request through `new-run/status/advance`.
- current_module: project generation fast path registry, non-web materializers, attribution writer, and concrete benchmark runners.
- downstream: generated `project_output`, benchmark reports, review pack, and repo verification.
- source_of_truth: `meta/tasks/CURRENT.md`, user Phase 15 request, ordinary project pipeline docs, and benchmark validators.
- fallback: fail closed with benchmark/report evidence; do not substitute agent-project/scaffold or mock success.
- acceptance_test: non-web matrix, concrete/full-stack benchmarks, agent benchmarks, unittest discover, workflow/module/patch/code-health, and verify repo.
- forbidden_bypass: no agent-project substitution, no fake CLI/file/test success, no fixture weakening, no source_generation skip.
- user_visible_effect: users can review non-web generated projects plus attribution and review pack evidence.
- ordinary mainline: `new-run/status/advance` used by non-web, concrete matrix, full-stack, and issue tracker benchmarks.
- agent substitution: `used_agent_project=false`, `used_agent_scaffold=false`, and `used_local_agent_runtime=false` recorded in attribution artifacts.
- benchmark integration: non-web matrix `4/4`, full-stack `2/2`, concrete matrix `3/3`, issue tracker `passed`, agent planner/runtime/factory `passed`.
- remaining gate: none; canonical repo verify passed with `verify_repo.ps1 -Profile code`.

## Check/Contrast/Fix Loop Evidence

- check: non-web matrix, focused tests, full-stack benchmark, concrete matrix, concrete issue benchmark, agent benchmarks, and unittest discover have passed.
- contrast: existing concrete benchmarks prove Web/API/full-stack but not CLI/package/game project generation or explicit attribution.
- fix: added non-web fast paths, attribution writer, review pack, benchmark/report wiring, and task-card integration evidence.

## Completion Criteria Evidence

- connected + accumulated + consumed.
- connected: ordinary project source_generation now emits attribution and all benchmark reports surface it.
- accumulated: non-web matrix and review pack summarize per-project attribution, validation, and artifact paths.
- consumed: focused tests and matrix/full-stack/concrete benchmark validators assert attribution, generated tests, and runtime behavior.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new reusable issue memory entry required; this was a bounded project-generation benchmark expansion.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: scoped repo workflow change requiring task binding, implementation, verification, and report evidence.
- skillized: no.
- reason: this task adds local benchmark/project-generation support, not a reusable operator workflow.
