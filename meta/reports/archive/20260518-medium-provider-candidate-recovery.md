# Report - Medium Provider Candidate Recovery

### Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_medium_candidate.py`
- `tools/providers/project_generation_live_full_candidate.py`
- `tools/providers/project_generation_attribution.py`
- `tools/providers/project_generation_source_stage.py`
- `tests/live_provider_medium_project_benchmark/run_live_provider_medium_project_benchmark.py`
- `tests/live_provider_blind_matrix/run_live_provider_blind_matrix.py`
- `tests/provider_assisted_benchmark/run_provider_assisted_benchmark.py`
- `tests/live_provider_full_candidate_benchmark/run_live_provider_full_candidate_benchmark.py`

### Plan

1. Replace medium single-shot provider candidate handling with staged plan -> manifest -> batched file synthesis -> assembly -> validation -> targeted repair.
2. Keep deterministic fallback honest and keep fallback out of provider medium success metrics.
3. Extend attribution, benchmark diagnostics, and Review Pack evidence with plan/manifest/batch/candidate fields.
4. Run targeted medium checks, then blind matrix, then full regression only after medium benchmark passes.

### Changes

- Added staged medium provider contract and helper functions in `tools/providers/project_generation_medium_candidate.py`.
- Routed medium live provider full-candidate cases through staged plan/manifest/batch synthesis in `tools/providers/project_generation_live_full_candidate.py`.
- Added targeted medium repair handling, capped provider-authored file ratio, and explicit fallback reasons.
- Extended attribution/source-stage evidence for provider plan, manifest, batch, raw response, validation, and repair report paths.
- Updated medium benchmark pass rules, diagnostics table, summary JSON, and Review Pack Phase 21B section.
- Fixed review-pack preservation across provider/full-candidate summary writers so Phase 20/21B evidence is not lost during regression tests.
- Updated blind repair test expectations to enforce the Phase 20 gate instead of a stale repaired-count-only threshold.

### Verify

- `.\.venv\Scripts\python.exe tests\live_provider_medium_project_benchmark\run_live_provider_medium_project_benchmark.py` -> PASS.
  - status: `passed`
  - provider_request_count: `12`
  - provider_plan_valid_count: `2`
  - provider_manifest_valid_count: `2`
  - provider_batch_count: `6`
  - provider_project_candidate_count: `2`
  - accepted/repaired/fallback/failed: `0/1/1/0`
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_candidate_staged_pipeline -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_candidate_batching -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_project_benchmark -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_project_attribution -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_project_validation -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_project_safety -v` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest tests.test_live_provider_medium_project_review_pack -v` -> PASS.
- `.\.venv\Scripts\python.exe tests\live_provider_blind_matrix\run_live_provider_blind_matrix.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\live_provider_full_candidate_benchmark\run_live_provider_full_candidate_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\live_provider_benchmark\run_live_provider_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\provider_assisted_benchmark\run_provider_assisted_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\non_web_project_matrix\run_non_web_matrix.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\full_stack_app_benchmark\run_full_stack_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\concrete_project_matrix\run_matrix_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\agent_planner_benchmark\run_planner_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` -> PASS.
- `.\.venv\Scripts\python.exe -m unittest discover tests -v` -> PASS, `802` tests, `4` skipped.
- `.\.venv\Scripts\python.exe scripts\workflow_checks.py` -> PASS.
- `.\.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> PASS.
- `.\.venv\Scripts\python.exe scripts\patch_check.py` -> PASS, `changed_files=228 max_files=240`.
- `.\.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> PASS.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> PASS.

## Workflow Evidence

- first failure point evidence: Phase 21 medium benchmark previously failed at provider medium success because both cases were fallback-only.
- minimal fix strategy evidence: first failing gate was medium provider success; smallest repair was staged medium synthesis plus bounded targeted repair and attribution, not fixture changes or deterministic fast-path expansion.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` is represented in full discover coverage; no separate failure observed.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` not required as a standalone repair gate; no new issue-memory entry required.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` not required as a standalone repair gate; `ctcp-workflow` was read and used.

### Questions

- None.

### Demo

- Medium benchmark report: `tests/live_provider_medium_project_benchmark/benchmark_report.md`.
- Medium summary: `tests/live_provider_medium_project_benchmark/generated/live_provider_medium_project_summary.json`.
- Blind matrix report: `tests/live_provider_blind_matrix/benchmark_report.md`.
- Full candidate report: `tests/live_provider_full_candidate_benchmark/benchmark_report.md`.
- Review Pack: `meta/reports/REVIEW_PACK.md`.
