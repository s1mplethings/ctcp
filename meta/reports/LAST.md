# Demo Report - LAST

## Latest Report

- File: [`meta/reports/archive/20260414-annotation-review-workbench.md`](archive/20260414-annotation-review-workbench.md)
- Date: `2026-04-14`
- Topic: `Generate and deliver a real Annotation Review Workbench`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/support_public_delivery.py`
- `scripts/delivery_replay_validator.py`
- `tests/support_virtual_delivery_e2e_runner.py`
- user-provided Annotation Review Workbench brief

### Plan
1. Use CTCP's own project-generation normalizers on a fresh D-drive run instead of hand-coding the project output.
2. Fix only the first generator bug that blocks generic GUI project source_generation.
3. Regenerate the Annotation Review Workbench run, export smoke outputs, and drive virtual public delivery plus cold replay.
4. Rerun workflow and repo-level gates, then report the earliest remaining gap against the user's product brief.

### Changes
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `tools/providers/project_generation_generic_archetypes.py`
- `tests/test_project_generation_artifacts.py`

### Verify
- `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` -> `0`
- `python scripts/workflow_checks.py` -> `pending rerun after report finalization`
- first failure point: `the generated generic GUI launcher rejected its own export probe because run_project_gui.py did not accept --headless`
- root cause class: `repo generator template bug in generic GUI launcher, followed by a product-capability gap because the generated project remained a generic pipeline fallback instead of a real annotation workbench`
- minimal fix strategy: `patch only the generic launcher template to accept --headless, regenerate the run, then measure the generated product against the original annotation requirements without hand-editing project code`
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json` -> `0`
- `python D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\project_output\build-a-local-interactive-annotation-review-work\scripts\run_project_gui.py --goal "annotation smoke" --project-name "Annotation Review Workbench" --out D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\artifacts\smoke_export --headless` -> `0`
- `python simlab/run.py --suite lite` -> `pending rerun after report finalization`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `1` (`workflow_checks` blocked first because LAST.md was missing triplet evidence; rerun pending after this report update)

### Questions
- None.

### Demo
- generated run root: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated`
- generated project root: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\project_output\build-a-local-interactive-annotation-review-work`
- generated project package: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\artifacts\support_exports\build-a-local-interactive-annotation-review-work.zip`
- final screenshot: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\project_output\build-a-local-interactive-annotation-review-work\artifacts\screenshots\final-ui.png`
- smoke export: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\artifacts\smoke_export\deliverables`
- delivery manifest: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\artifacts\support_public_delivery.json`
- replay report: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\artifacts\delivery_replay\replay_artifacts\replay_report.json`
- replay screenshot: `D:\ctcp_runs\ctcp\20260414-annotation-review-workbench-generated\artifacts\delivery_replay\replay_artifacts\replayed_screenshot.png`
- product-gap note: `the generated project exports project_bundle/workflow_plan/acceptance_report only; it does not implement image loading, bbox editing, save/restore, or YOLO export`

### Integration Proof
- upstream: `user brief -> external run_dir project`
- current_module: `CTCP project-generation templates + generated run + support delivery + replay report`
- downstream: `final answer with artifact paths and the first unmet product requirement`
- source_of_truth: `generated source files, source_generation/project_manifest artifacts, smoke export deliverables, and support_public_delivery/replay outputs`
- fallback: `if CTCP generation cannot reach the requested domain, stop at the earliest unmet requirement and still preserve package/delivery/replay evidence`
- acceptance_test:
  - `generated project smoke export`
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - `do not hand-code the generated project`
  - `do not fake annotation behavior that CTCP itself did not generate`
  - `do not skip package/delivery/replay evidence even if the product brief is only partially met`
- user_visible_effect: `the user can inspect the exact project CTCP generated, plus its package, screenshot, delivery manifest, and replay report, and can see the first unmet annotation-workbench requirement without black-box guessing`
