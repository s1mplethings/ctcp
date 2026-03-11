# Update 2026-03-07 - Markdown Contract Drift Fix

### Readlist
- `README.md`
- `AGENTS.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/25_project_plan.md`
- `docs/30_artifact_contracts.md`
- `docs/12_modules_index.md`
- `docs/13_contracts_index.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `meta/backlog/execution_queue.json`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- `scripts/sync_doc_links.py`

### Drift / Naming Conflicts Identified
1. Verify contract naming drift:
   `docs/03_quality_gates.md` still treated `proof.json` as hard gate artifact, while `verify_repo.*` does not implement that rule.
2. Verify gate scope drift:
   `AGENTS.md` documented `web build` as required gate, but current `verify_repo.*` implementation does not run a web build stage.
3. Artifact authority ambiguity:
   `verify_report.json` / `proof.json` / `verify_report.md` lacked a single canonical authority statement across core docs.
4. Headless-vs-GUI narrative drift:
   core docs were not uniformly explicit that GUI is optional and non-blocking for default DoD path.
5. Contracts index coverage gap:
   `docs/13_contracts_index.md` did not cover main ADLC chain artifacts (`find_result.json`, PLAN pair, verify report, dispatch config, failure bundle).
6. Planning discipline gap:
   `CURRENT.md` used `Queue Item: N/A`, while project plan required queue binding with no explicit legal exception.
7. Index curation gap:
   `scripts/sync_doc_links.py` omitted key docs (`docs/25_project_plan.md`, `docs/20_conventions.md`).

### Plan
1) Unify verify contract names and gate scope wording to script-aligned behavior.
2) Re-anchor workflow narrative as headless-first, GUI-optional in core docs.
3) Repair doc index and contract index coverage.
4) Close queue discipline loop across project plan/template/current/queue.
5) Run doc index check + verify gate and record first failure point.

### Changes (File-Level)
- `docs/00_CORE.md`
  - Rewritten into structured sections (purpose/roles/artifacts/gates).
  - Declared canonical verify artifact `artifacts/verify_report.json`.
  - Downgraded `proof.json` + `verify_report.md` to compatibility/non-authoritative status.
  - Aligned DoD gate list with current `verify_repo.ps1/.sh` behavior.
- `docs/03_quality_gates.md`
  - Removed outdated `scripts/verify.*` + mandatory `proof.json` assertions.
  - Added script-aligned gate sequence and optional full gate semantics.
- `docs/30_artifact_contracts.md`
  - Added global verify naming policy and compatibility wording.
  - Marked `artifacts/verify_report.json` as canonical verify artifact.
- `README.md`
  - Added explicit verify naming contract section.
  - Synced Doc Index block to curated list (including `docs/20_conventions.md`, `docs/25_project_plan.md` and AI context docs).
- `AGENTS.md`
  - Synced verify coverage list to real gate sequence.
  - Added canonical verify artifact and compatibility wording (`proof.json`/`verify_report.md`).
- `ai_context/CTCP_FAST_RULES.md`
  - Added canonical verify naming and compatibility policy.
- `docs/02_workflow.md`
  - Explicitly stated headless/offline-first mainline and GUI optional path.
  - Added canonical verify artifact path in standard artifact paths.
- `docs/12_modules_index.md`
  - Marked UI/visualization modules as optional non-DoD mainline.
- `scripts/sync_doc_links.py`
  - Expanded `CURATED_DOCS` with missing key docs (`docs/25_project_plan.md`, `docs/20_conventions.md`, fast rules/problem/decision logs).
- `docs/13_contracts_index.md`
  - Rebuilt contracts index to cover ADLC critical artifact chain and verify compatibility policy.
- `docs/25_project_plan.md`
  - Added hard queue-binding rule and `N/A` prohibition.
  - Defined ADHOC queue item path for direct user tasks.
- `meta/tasks/TEMPLATE.md`
  - Added reusable template guidance + minimal example.
  - Enforced queue binding rule (no `Queue Item: N/A`).
- `meta/tasks/CURRENT.md`
  - Updated active task binding to `L0-PLAN-001`.
  - Replaced top section with current docs-contract task scope and DoD mapping.
- `meta/backlog/execution_queue.json`
  - Updated `L0-PLAN-001` DoD/notes wording to reflect queue-discipline closure objective.
- `ai_context/problem_registry.md`
  - Converted to reusable template with usage guidance + examples.
- `ai_context/decision_log.md`
  - Converted to reusable template with usage guidance + example decision entry.

### Verify
- `python scripts/sync_doc_links.py --check` => exit 0 (`[sync_doc_links] ok`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1
  - first failure: `cmake configure (headless lite)` cannot write `build_lite` (permission denied).
- `CTCP_BUILD_ROOT=...\\build_verify_tmp ; powershell -File scripts/verify_repo.ps1` => exit 1
  - first failure: `lite scenario replay` cannot create default run root under `%LOCALAPPDATA%\\ctcp\\runs` (permission denied).
- `CTCP_BUILD_ROOT=...\\build_verify_tmp ; CTCP_RUNS_ROOT=...\\build_verify_tmp\\runs ; powershell -File scripts/verify_repo.ps1` => exit 1
  - first failure: lite replay scenario suite failed (`passed=11 failed=3`).
- `CTCP_BUILD_ROOT=...\\build_verify_tmp ; CTCP_RUNS_ROOT=...\\build_verify_tmp\\runs ; CTCP_SKIP_LITE_REPLAY=1 ; powershell -File scripts/verify_repo.ps1` => exit 1
  - first failure: `python unit tests` (2 failures + 2 errors), including:
    - `meta/run_pointers/LAST_RUN.txt` write permission errors in orchestrator tests.
    - dataset reply mismatch failures in `test_telegram_cs_bot_dataset_v1`.

### Questions
- None.

### Demo
- Report file: `meta/reports/LAST.md`
- Task file: `meta/tasks/CURRENT.md`
- Queue file: `meta/backlog/execution_queue.json`
- Last verify run root used for replay: `D:/.c_projects/adc/ctcp/build_verify_tmp/runs/ctcp/simlab_runs/20260307-135858`

## Goal
- Align lite scenarios to canonical mainline (S17-S19 linear) and allow manual_outbox for patchmaker/fixer.

## Readlist
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/30_artifact_contracts.md`
- `docs/PATCH_CONTRACT.md`
- `AGENTS.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`

## Plan
1) Docs/Spec first (task + report update)
2) Implement (dispatch provider fix, update tests, replace S17-S19 scenarios, remove S20-S25)
3) Verify (`python -m compileall .`, `python simlab/run.py --suite lite`, `scripts/verify_repo.ps1`)
4) Report (update `meta/reports/LAST.md`)

## Changes
- Updated `scripts/ctcp_dispatch.py` to allow manual_outbox for patchmaker/fixer.
- Updated `tests/test_mock_agent_pipeline.py` expectations for manual_outbox fallback.
- Replaced lite scenarios:
  - Added `simlab/scenarios/S17_lite_linear_mainline_resolver_only.yaml`
  - Added `simlab/scenarios/S18_lite_linear_mainline_resolver_plus_web.yaml`
  - Added `simlab/scenarios/S19_lite_linear_robustness_tripwire.yaml`
  - Removed legacy `simlab/scenarios/S17_lite_patch_first_reject.yaml`
  - Removed legacy `simlab/scenarios/S18_lite_link_researcher_find_web_outbox.yaml`
  - Removed legacy `simlab/scenarios/S19_lite_link_librarian_context_pack_outbox.yaml`
  - Removed legacy `simlab/scenarios/S20_lite_link_contract_guardian_review_outbox.yaml`
  - Removed legacy `simlab/scenarios/S21_lite_link_cost_controller_review_outbox.yaml`
  - Removed legacy `simlab/scenarios/S22_lite_link_patchmaker_diff_patch_outbox.yaml`
  - Removed legacy `simlab/scenarios/S23_lite_robust_idempotent_outbox_no_duplicates.yaml`
  - Removed legacy `simlab/scenarios/S24_lite_robust_patch_scope_violation_rejected.yaml`
  - Removed legacy `simlab/scenarios/S25_lite_robust_invalid_find_web_json_blocks.yaml`
- Updated `meta/tasks/CURRENT.md` for this run.

## Verify
- `python -m compileall .` => exit 0
- `python simlab/run.py --suite lite` => exit 0
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-005505` (passed=11 failed=0)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 0
  - lite scenario replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-005925` (passed=11 failed=0)

## TEST SUMMARY
- Commit: 5b6ec78
- Commands Run:
  - `python -m compileall .` (exit 0)
  - `python simlab/run.py --suite lite` (exit 0)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (exit 0)
- SimLab lite: PASS (total=11, passed=11, failed=0)
- New/updated scenarios:
  - S17_lite_linear_mainline_resolver_only: PASS
  - S18_lite_linear_mainline_resolver_plus_web: PASS
  - S19_lite_linear_robustness_tripwire: PASS

## Questions
- None

## Demo
- Report: `meta/reports/LAST.md`
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- SimLab summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-005925/summary.json`

