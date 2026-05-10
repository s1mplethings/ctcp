# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260510-vn-output-contract-team-pm-false-positive.md`
- Date: `2026-05-10`
- Topic: `VN Output Contract Team PM False Positive`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `docs/12_virtual_team_contract.md`
- `docs/04_execution_flow.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_decisions.py`
- `tools/providers/project_generation_narrative_spec.py`
- `tests/test_project_generation_narrative_contract.py`
- `tests/test_plane_lite_benchmark_regression.py`
- `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b\TRACE.md`
- `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b\artifacts\source_generation_report.json`

### Plan
1. Bind the false-positive repair task.
2. Add focused regression coverage for VN narrative asset text containing `board`.
3. Narrow the hard team PM guard to user goal / resolved intent / resolved domain instead of full provider-generated story and asset prose.
4. Add narrative VN structural defaults required by project-generation gates.
5. Run focused and Plane-lite regressions.
6. Retry the VN customer run through orchestrator without manual generated-source edits.
7. Run workflow/module/patch/code-health gates and archive evidence.

### Changes
- Added `tools/providers/project_generation_narrative_spec.py`.
- Updated `tools/providers/project_generation_artifacts.py` so incidental VN prose such as `timetable board` does not trigger Plane-lite/team PM enforcement.
- Updated `tools/providers/project_generation_decisions.py` so narrative VN contracts fill required non-empty structural lists.
- Added `tests/test_project_generation_narrative_contract.py`.

### Verify
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_project_generation_narrative_contract -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_project_generation_artifacts.ProjectGenerationArtifactTests.test_output_contract_freeze_production_narrative_request_is_not_benchmark_default -v` returned 0, 1 test OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_plane_lite_benchmark_regression -v` returned 0, 16 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 1 because direct edits grew oversized files.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0 after extracting focused files.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- RUN: `scripts\ctcp_orchestrate.py advance --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b --max-steps 20` reached `source_generation_report.json`; the shell command timed out at 30 minutes after evidence was written, and two matching orphaned advance processes were stopped.
- STATUS: `scripts\ctcp_orchestrate.py status --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b` reports `blocked: generic_validation.passed must be true`.
- FIRST FAILURE: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 1 at `lite scenario replay`; prior gates passed, then replay reported 11 passed and 4 failed scenarios.
- SimLab first failure: `S13_lite_dispatch_outbox_on_missing_review`, step 6 expected `owner=Contract Guardian`.
- Failure evidence: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-161139\summary.json`, `...\S13_lite_dispatch_outbox_on_missing_review\TRACE.md`, and `...\S13_lite_dispatch_outbox_on_missing_review\failure_bundle.zip`.

### Questions
- None.

### Demo
- External run: `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b`.
- API provenance: provider ledger shows all critical steps used `api_agent` with fallback count 0.
- Generated-source status: provider-authored source applied, `generated_business_file_count=21`, source customization completion passed.
- VN content evidence: generated project includes story, scene graph, cast, background/sprite asset catalog paths, and sample data under `project_output/generate-a-runnable-visual-novel-application-pac`.
- Current blocker: generated project is not deliverable yet because generic validation fails on import/interface/test mismatches and missing real visual/preview evidence.

### Integration Proof
- connected: VN customer request advanced through Virtual Team contract freeze into source_generation.
- accumulated: narrative contract defaults now preserve VN domain shape and satisfy structural spec gates.
- consumed: orchestrator consumed the repaired contract path and reached source_generation.

### First Failure And Repair
- first failure point evidence: output_contract_freeze rejected VN prose as Plane-lite/team PM because generated asset text contained broad `board` wording.
- minimal fix strategy evidence: narrow hard team-PM request detection and add narrative structural defaults; do not hand-patch generated VN source.
- next blocker: source_generation generic validation fails on provider-generated source consistency and visual evidence.

### Verify Failure Bundle
- command: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
- return code: `1`
- first failing gate: `lite scenario replay`
- first failing check: `S13_lite_dispatch_outbox_on_missing_review`, step 6 missing `owner=Contract Guardian`.
- minimal fix strategy: repair the support/status owner text regression in a separate task; this patch should stay scoped to VN output-contract generation.

### Skill Decision
- skill used: `ctcp-workflow`.
- reason: repo code/tests and generation-run evidence changed under CTCP queue discipline.
- skillized: no.
- persona_lab_impact: none.
