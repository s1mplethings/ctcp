# Demo Report - Provider Src Layout Runtime Probe

## Latest Report

- File: `meta/reports/archive/20260503-provider-src-layout-runtime-probe.md`
- Date: `2026-05-03`
- Topic: `Provider Src Layout Runtime Probe`

### Readlist
- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_source_helpers.py`
- `tools/providers/project_generation_validation.py`
- `tests/test_project_generation_artifacts.py`
- latest live run `20260503-174746-202806-orchestrate`

### Plan
1. Confirm the live blocker from the latest source generation report.
2. Make runtime probes launch generated GUI/web entrypoints with project `src` on `PYTHONPATH`.
3. Add a GUI-only fallback from rich export args to plain `--headless` when the generated entrypoint rejects extra CLI args.
4. Stop treating `asset_placeholders.json` as unfinished solely because it contains asset placeholder identifiers.
5. Add focused regressions and run current-task gates.

### Changes
- `tools/providers/project_generation_source_helpers.py`
  - `_run_command_capture(...)` now accepts per-probe environment overrides.
  - GUI/web runtime probes run from the generated project root with `<project>/src` prepended to `PYTHONPATH`.
  - GUI export probes retry `python <entry> --headless` only when the richer export command fails due unsupported CLI options.
- `tools/providers/project_generation_validation.py`
  - `asset_placeholders.json` is allowed to contain placeholder asset identifiers without being counted as placeholder-only source.
  - Real TODO/stub/not-implemented markers are still rejected.
- `tests/test_project_generation_artifacts.py`
  - Added a regression for `src` layout GUI entrypoints that only support `--headless`.
  - Added a regression for asset placeholder catalog validation.

### Verify
- Passed:
  - `python -m py_compile tools\providers\project_generation_source_helpers.py tools\providers\project_generation_validation.py tests\test_project_generation_artifacts.py`
  - `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_runtime_checks_support_src_layout_gui_entrypoint -v`
  - `$env:PYTHONPATH=(Get-Location).Path; python tests\test_project_generation_artifacts.py -k test_generic_validation_allows_asset_placeholder_catalog_file -v`
  - `python scripts\workflow_checks.py`
  - `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
- First failure point evidence:
  - Running the focused tests without `PYTHONPATH` failed before test execution with `ModuleNotFoundError: No module named 'tools'`; rerunning with the repo root in `PYTHONPATH` passed.
- minimal fix strategy evidence:
  - Keep the patch limited to probe process environment, GUI headless fallback, and asset placeholder catalog validation; do not restore local templates or synthesize generated business files locally.
- Canonical verify status:
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` passed CMake configure/build, ctest lite, and workflow gate, then failed at module protection.
  - first canonical failure: pre-existing out-of-scope dirty files are outside CURRENT.md Allowed Write Paths: `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, `tests/test_runtime_wiring_contract.py`.
  - minimal fix strategy evidence: keep this task scoped to provider runtime probes; close or rebind those support-lane dirty files in a separate task rather than widening this patch.
- triplet runtime wiring command evidence:
  - `test_runtime_wiring_contract.py` was not rerun separately in this narrow runtime-probe task.
- triplet issue memory command evidence:
  - `test_issue_memory_accumulation_contract.py` was not rerun separately; no issue memory change was made.
- triplet skill consumption command evidence:
  - `test_skill_consumption_contract.py` was not rerun separately; no skill contract change was made.

### Questions
- None.

### Demo
- Latest VN run already produced API-authored source after source-generation retry; it was blocked because the validator launched the generated `src` layout entrypoint without import path setup.
- Manual smoke evidence from the live run: setting `PYTHONPATH=<project>/src` and running the generated GUI script with `--headless` returned rc 0.
- With this patch, the next generated `src` layout GUI project should not be blocked by `No module named '<package>'` when the project is otherwise runnable.
- Telegram bot was restarted on the patched code as PID pair `34396 / 28232`; startup stderr confirms local support history was cleared under the temp CTCP runs root.

### Integration Proof
- connected: generated project `src` layout is connected to runtime probe process environment.
- accumulated: runtime checks retain final probe result and fallback metadata when rich GUI args are unsupported.
- consumed: `generic_validation` consumes the corrected probe result and no longer fails on valid asset placeholder catalogs.
