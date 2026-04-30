# Benchmark Pass Contracts

This document defines the pass/fail contracts used by `scripts/formal_benchmark_runner.py`.

## Shared Rules

Both formal benchmarks require:

- true API only: `CTCP_FORCE_PROVIDER=api_agent`
- formal execution lock: `CTCP_FORMAL_API_ONLY=1`
- no local-provider exception on critical steps (including `librarian/context_pack`)
- no `mock_agent`
- at least one successful remote API request recorded in `api_calls.jsonl`
- no fallback result accepted as a passed true-API step
- `artifacts/provider_ledger.jsonl` exists
- `artifacts/provider_ledger_summary.json` exists
- `provider_ledger_summary.critical_step_count > 0`
- `provider_ledger_summary.all_critical_steps_api = true`
- workflow id: `wf_project_generation_manifest`
- project domain: `team_task_management`
- project type: `team_task_pm`
- project archetype: `team_task_pm_web`
- acceptance triplets present under `artifacts/acceptance/**/`
- acceptance ledger present
- `artifacts/verify_report.json` result is `PASS`
- `artifacts/support_public_delivery.json` completion gate passed
- cold replay passed
- `artifacts/final_project_bundle.zip` exists
- `artifacts/intermediate_evidence_bundle.zip` exists
- final `RUN.json.status=pass`

## formal_basic_benchmark

The basic formal regression is the standard Plane-lite team task management benchmark.

Pass requires all shared rules plus:

- benchmark source is `plane_lite_team_pm_test_pack.zip`
- scripted turns are consumed in order
- the generated project is not a generic web-service scaffold
- the project includes the benchmark MVP shape:
  - local login or minimal local auth flow
  - workspace or project concept
  - task CRUD
  - board view
  - list view
  - task detail
  - title, description, status, priority, assignee, due date, labels
  - comments or activity log
  - basic filtering
  - demo data
  - README and startup steps
  - at least one final screenshot
  - final packaged artifact

## formal_hq_benchmark

The high-quality formal regression is an extended product-depth profile over the same Plane-lite direction.

Pass requires all shared rules plus:

- `build_profile=high_quality_extended`
- `product_depth=extended`
- `required_pages >= 8`
- `required_screenshots >= 8`
- `artifacts/extended_coverage_ledger.json` exists
- `extended_coverage_ledger.passed=true`
- feature matrix present
- page map present
- data model summary present
- dashboard or project overview present
- search present
- import/export coverage present
- screenshot coverage count at least 8
- page depth includes:
  - Dashboard
  - Project list
  - Project overview
  - Task list
  - Kanban board
  - Task detail
  - Activity feed
  - Settings or project configuration

## formal_endurance_benchmark

The endurance formal regression is the long-chain Indie Studio Production Hub benchmark.

Pass requires:

- true API only: `CTCP_FORCE_PROVIDER=api_agent`
- formal execution lock: `CTCP_FORMAL_API_ONLY=1`
- no local-provider exception on critical steps (including `librarian/context_pack`)
- no `mock_agent`
- `artifacts/provider_ledger.jsonl` exists
- `artifacts/provider_ledger_summary.json` exists
- `provider_ledger_summary.critical_step_count > 0`
- `provider_ledger_summary.all_critical_steps_api = true`
- workflow id: `wf_project_generation_manifest`
- project domain: `indie_studio_production_hub`
- project type: `indie_studio_hub`
- project archetype: `indie_studio_hub_web`
- non-empty legal `package_name`
- `artifacts/source_generation_report.json` exists and records:
  - `status=pass`
  - `generic_validation.passed=true`
  - `python_syntax.passed=true`
- acceptance triplets present and complete
- no fallback result accepted as a passed true-API step
- `artifacts/verify_report.json` result is `PASS`
- `artifacts/support_public_delivery.json` records:
  - `internal_runtime_status=PASS`
  - `user_acceptance_status=PASS`
  - delivery completion passed
  - cold replay passed
- `artifacts/final_project_bundle.zip` exists
- `artifacts/intermediate_evidence_bundle.zip` exists
- `artifacts/extended_coverage_ledger.json` exists with `passed=true`
- pages actual `>= 12`
- screenshots actual `>= 10`
- coverage includes:
  - feature matrix
  - page map
  - data model summary
  - milestone plan
  - startup guide
  - replay guide
  - mid-stage review
  - Asset Library
  - Asset Detail
  - Bug Tracker
  - Build / Release Center
  - Docs Center
- final `RUN.json.status=pass`

## Verdicts

- `PASS`: every required gate for the selected profile passed.
- `FAIL`: at least one hard gate failed. The summary records `first_failure_point`.
- `PARTIAL`: reserved for human reports when a run is useful but fails a hard gate; the machine summary currently emits PASS or FAIL.

## Provider Ledger Audit Fields

Formal benchmark evaluation relies on the run-level provider ledger. Each critical step must be auditable with at least:

- `role`
- `action`
- `provider_used`
- `external_api_used`
- `request_id` when present
- `fallback_used`
- `local_function_used` when present
- `verdict`

If any non-exempt critical step is not `api_agent`, uses fallback, uses a local function, or lacks API evidence, the benchmark summary must not report PASS.

## Repo-Level Verify Separation

Do not use benchmark PASS as a substitute for repo-level canonical verify.

The benchmark summary includes `repo_level_verify_note` to make this separation explicit. Repo-level `scripts/verify_repo.ps1` failures must be reported as repo gate failures, not benchmark failures, unless they directly prevent the benchmark run from executing.
