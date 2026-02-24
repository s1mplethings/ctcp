# Demo Report - LAST

## Goal
- 新增/强化 deterministic 的 agent 连接与 ADLC 鲁棒性场景（S17~S25），并保持 `verify_repo` 与 `simlab lite` 全绿。

## Readlist
- `ai_context/00_AI_CONTRACT.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/00_CORE.md`
- `docs/30_artifact_contracts.md`

## Plan
1) Docs/Spec first：更新任务单并对齐 artifact/outbox 合同  
2) Implement：新增 SimLab `S17..S25`（连接性 + 鲁棒性）  
3) Verify：`compileall` + `simlab --suite lite` + `verify_repo.ps1`  
4) Report：回填任务单与 LAST 报告

## Changes
- 更新场景：
  - `simlab/scenarios/S17_lite_patch_first_reject.yaml`（替换为 `S17_lite_link_chair_analysis_outbox`）
  - 新增 `simlab/scenarios/S18_lite_link_researcher_find_web_outbox.yaml`
  - 新增 `simlab/scenarios/S19_lite_link_librarian_context_pack_outbox.yaml`
  - 新增 `simlab/scenarios/S20_lite_link_contract_guardian_review_outbox.yaml`
  - 新增 `simlab/scenarios/S21_lite_link_cost_controller_review_outbox.yaml`
  - 新增 `simlab/scenarios/S22_lite_link_patchmaker_diff_patch_outbox.yaml`
  - 新增 `simlab/scenarios/S23_lite_robust_idempotent_outbox_no_duplicates.yaml`
  - 新增 `simlab/scenarios/S24_lite_robust_patch_scope_violation_rejected.yaml`
  - 新增 `simlab/scenarios/S25_lite_robust_invalid_find_web_json_blocks.yaml`
- 门禁记录同步：
  - `meta/tasks/CURRENT.md`（DoD/Acceptance 勾选与结果回填）

## Verify
- `python simlab/run.py --suite lite` => PASS
  - `{"run_dir":"C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260224-194834","passed":17,"failed":0}`
- `python -m compileall .` => PASS
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1` => PASS
  - `workflow gate (workflow checks): ok`
  - `plan check: ok`
  - `patch check: ok (changed_files=53 max_files=200)`
  - `behavior catalog check: ok`
  - `contract checks: ok`
  - `doc index check: ok`
  - `lite scenario replay: passed=17 failed=0`
  - `python unit tests: Ran 46 tests ... OK (skipped=3)`
  - `[verify_repo] OK`

## Questions
- None

## Demo
- Report: `meta/reports/LAST.md`
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- SimLab summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260224-195209\summary.json`
