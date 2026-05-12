# External Agent Factory Benchmark Report

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `README.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `scripts/ctcp_orchestrate.py`
- `scripts/resolve_workflow.py`
- `workflow_registry/index.json`
- `workflow_registry/wf_project_generation_manifest/recipe.yaml`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_source_stage.py`
- `tests/test_project_generation_artifacts.py`

## Plan
1. Bind an additive Delivery Lane benchmark task.
2. Discover real CTCP entrypoints, dependency files, test commands, schemas, and generation logic.
3. Add the six fixed external QA benchmark fixtures.
4. Add independent schema, permission, workflow, and tool validators.
5. Add a benchmark runner that invokes real CTCP code and writes generated outputs.
6. Run the benchmark and record pass/fail/unsupported evidence.
7. Run focused gates and canonical verify.

## Changes
- Added `tests/agent_factory_benchmark/fixtures/*.json`.
- Added `tests/agent_factory_benchmark/validators/*.py`.
- Added `tests/agent_factory_benchmark/run_benchmark.py`.
- Added generated benchmark outputs under `tests/agent_factory_benchmark/generated/`.
- Added `tests/agent_factory_benchmark/benchmark_report.md`.
- Updated CTCP meta task/report records for this benchmark.

## Verify
- PASS: `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` returned 0 with `pass_count=0`, `fail_count=0`, `unsupported_count=6`.
- PASS: `.venv\Scripts\python.exe -m py_compile tests\agent_factory_benchmark\run_benchmark.py tests\agent_factory_benchmark\validators\schema_validator.py tests\agent_factory_benchmark\validators\permission_validator.py tests\agent_factory_benchmark\validators\workflow_validator.py tests\agent_factory_benchmark\validators\tool_validator.py` returned 0.
- FAIL then fixed: `.venv\Scripts\python.exe scripts\workflow_checks.py` first returned 1 because `CURRENT.md` lacked mandatory 10-step evidence sections.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after adding the evidence sections.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0.
- canonical verify details: headless lite build and ctest passed; workflow/module/prompt/plan/patch/behavior/contract/doc-index/code-health/triplet guards passed; lite replay skipped by env; Python unit tests ran 550 tests with 4 skipped.
- triplet runtime wiring command evidence: `test_runtime_wiring_contract.py` passed inside canonical verify, 25 tests OK.
- triplet issue memory command evidence: `test_issue_memory_accumulation_contract.py` passed inside canonical verify, 3 tests OK.
- triplet skill consumption command evidence: `test_skill_consumption_contract.py` passed inside canonical verify, 3 tests OK.

## Questions
- None.

## Demo
- Report: `tests/agent_factory_benchmark/benchmark_report.md`.
- Generated outputs: `tests/agent_factory_benchmark/generated/output_*.json`.
- Summary: `tests/agent_factory_benchmark/generated/benchmark_summary.json`.
- Result: all six benchmark cases are `unsupported`, not passed, because CTCP does not expose an agent-manifest generation entrypoint or output contract.

## First Failure And Repair
- first failure point evidence: workflow gate failed on missing 10-step evidence sections in `CURRENT.md`.
- repair: added Check/Contrast/Fix Loop, Completion Criteria, Issue Memory Decision, and Skill Decision evidence.
- minimal fix strategy: keep the benchmark additive and do not alter core generation logic to make results pass.

## Check/Contrast/Fix Loop Evidence
- check: benchmark runner executed the six fixed cases and wrote generated outputs plus report.
- contrast: CTCP ran successfully but routed inputs to generic project-generation artifacts, not agent manifest output.
- fix: no core behavior was changed; unsupported is the correct benchmark result for the current product surface.
- re-check: py_compile, workflow, module protection, patch, code health, and canonical verify passed after evidence repair.

## Completion Criteria Evidence
- completion criteria evidence: connected + accumulated + consumed.
- connected: benchmark runner invokes `scripts/resolve_workflow.py` and real project-generation normalizer/source-generation functions.
- accumulated: fixture inputs, generated outputs, validator results, summary JSON, and report are persisted under `tests/agent_factory_benchmark/`.
- consumed: validators consume generated outputs and write pass/fail/unsupported evidence into the report.

## Issue Memory Decision Evidence
- issue memory decision evidence: no new issue-memory entry.
- reason: unsupported agent-manifest generation is a benchmark finding and product capability gap, not a recurring repaired runtime defect.

## Skill Decision
- skill used: `ctcp-workflow`.
- reason: CTCP task binding, scoped implementation, gate execution, and auditable reporting were required.
- skillized: no, because the benchmark is repo-local QA evidence. It should become a reusable skill only if this external benchmark workflow is repeatedly requested across repos.
- persona_lab_impact: none.
