# Demo Report - Provider Sample Schema And Headless Visual Evidence

## Latest Report

- File: `meta/reports/archive/20260503-provider-sample-schema-visual-evidence.md`
- Date: `2026-05-03`
- Topic: `Provider Sample Schema And Headless Visual Evidence`

### Readlist
- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_sample_metrics.py`
- `tools/providers/project_generation_source_helpers.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_validation.py`
- `tests/test_project_generation_artifacts.py`
- latest live run `20260503-193149-962580-orchestrate`

### Plan
1. Confirm the latest run moved past runtime import failure.
2. Fix stale narrative sample metrics for provider-authored nested sample schema.
3. Reuse the same metrics in source-stage sample quality.
4. Collect successful `--headless` fallback export files for visual evidence when `--out` is unsupported.
5. Add focused regressions and run gates.

### Changes
- Added `tools/providers/project_generation_sample_metrics.py`.
- `tools/providers/project_generation_validation.py` now uses shared narrative sample metrics.
- `tools/providers/project_generation_source_stage.py` now uses the same metrics for sample quality.
- `tools/providers/project_generation_source_helpers.py` now copies successful GUI `--headless` fallback outputs into the visual evidence export directory.
- `tests/test_project_generation_artifacts.py` covers nested provider sample metrics and headless fallback visual evidence.

### Verify
- Passed:
  - `python -m py_compile tools\providers\project_generation_source_helpers.py tools\providers\project_generation_sample_metrics.py tools\providers\project_generation_source_stage.py tools\providers\project_generation_validation.py tests\test_project_generation_artifacts.py`
  - `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_narrative_sample_metrics_accept_provider_nested_schema -v`
  - `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_runtime_checks_support_src_layout_gui_entrypoint -v`
  - live-run recheck against `20260503-193149-962580-orchestrate`: updated domain validation passed with `scene_count=8`, `branch_point_count=2`, `valid_character_cards=3`; runtime visual evidence returned `visual_status=provided`, `visual_type=real_export_page`, and `gate_result.passed=true`.
  - `python scripts\workflow_checks.py`
  - `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
- First failure point evidence:
  - Before this patch, latest run had `generic_validation.passed=true`, startup/export rc 0, but `domain_validation.passed=false` because sample metrics read scene/branch/card counts as zero, and `gate_layers.result.passed=false` because no exported files were found in the temp visual evidence dir.
- minimal fix strategy evidence:
  - Keep the patch limited to schema-compatible sample metrics and headless fallback export evidence; do not restore local templates or manually rewrite generated project code.
- Canonical verify status:
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` passed CMake configure/build, ctest lite, and workflow gate, then failed at module protection.
  - first canonical failure: pre-existing out-of-scope dirty files are outside CURRENT.md Allowed Write Paths: `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, `tests/test_runtime_wiring_contract.py`.
- triplet runtime wiring command evidence:
  - `test_runtime_wiring_contract.py` was not rerun separately because it is one of the pre-existing out-of-scope dirty files blocking module protection.
- triplet issue memory command evidence:
  - `test_issue_memory_accumulation_contract.py` was not rerun separately; no issue memory change was made.
- triplet skill consumption command evidence:
  - `test_skill_consumption_contract.py` was not rerun separately; no skill contract change was made.

### Questions
- None.

### Demo
- Latest run `20260503-193149-962580-orchestrate` now passes the corrected checks when re-evaluated locally:
  - domain sample metrics: 3 characters, 4 chapters, 8 scenes, 2 branch choices, 8 scenes with backgrounds/media.
  - visual evidence: `project_output/vn/artifacts/screenshots/final-ui.png`.
- Existing blocked artifact in that run was created before this patch; a fresh Telegram request or explicit rerun is needed for the pipeline artifact to be regenerated through the new code.
- Telegram bot was restarted on the patched code as PID pair `18004 / 26184`; startup stderr confirms local support history was cleared under the temp CTCP runs root.

### Integration Proof
- connected: provider-authored nested sample schema connects to shared narrative metrics.
- accumulated: successful `--headless` fallback export files are accumulated into visual evidence inputs.
- consumed: source generation domain/result gates consume the corrected metrics and evidence path.
