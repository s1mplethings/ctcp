# Update 2026-02-26 (v2p_user_sim_testkit validation)

### Readlist
- Required contracts/docs:
  - `AGENTS.md`
  - `docs/00_CORE.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `ai_context/CTCP_FAST_RULES.md`
  - `README.md`
  - `BUILD.md`
  - `PATCH_README.md`
  - `TREE.md`
  - `docs/03_quality_gates.md`
  - `ai_context/problem_registry.md`
  - `ai_context/decision_log.md`
- Skill references:
  - `.agents/skills/ctcp-workflow/SKILL.md`
  - `.agents/skills/ctcp-verify/SKILL.md`
  - `.agents/skills/ctcp-failure-bundle/SKILL.md`
- Testkit docs from zip:
  - `v2p_user_sim_testkit.zip::README.md`
  - `v2p_user_sim_testkit.zip::TASK.md`
  - `v2p_user_sim_testkit.zip::docs/CONTRACT.md`
  - `v2p_user_sim_testkit.zip::simlab/scenarios/S99_v2p_user_sim_bench.yaml`

### Plan
1) Docs/Spec: update `meta/tasks/CURRENT.md` for this test-only task.
2) Gate precheck: run workflow/plan checks.
3) Execute user-sim kit in external run dir and validate outputs/thresholds.
4) Run acceptance gate `scripts/verify_repo.ps1`.
5) Record report and external evidence chain (`TRACE.md`, `artifacts/verify_report.json`).

### Changes
- Updated repo files:
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/run_pointers/LAST_RUN.txt`
- External run artifacts:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/TRACE.md`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/artifacts/verify_report.json`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/verify_repo.log`

### Verify
- `python scripts/workflow_checks.py` => exit `1` (first run), reason: existing code-dir changes in worktree required `CURRENT.md` to check `Code changes allowed`.
- `python scripts/workflow_checks.py` => exit `0` (after minimal task-card fix).
- `python scripts/plan_check.py` => exit `0`.
- `python run_all.py` (inside extracted testkit run dir) => exit `0`.
- Output/threshold check (JSON validation command) => exit `0`:
  - files exist: `out/cloud.ply`, `out/cloud_sem.ply`, `out/scorecard.json`, `out/eval.json`
  - `fps=6.81376221725911` (`> 1.0`)
  - `points_down=40022` (`>= 10000`)
  - `voxel_fscore=0.996370601875189` (`>= 0.85`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - first failure gate/check: `patch_check`
  - first failure message: `[patch_check][error] out-of-scope path (Scope-Allow): specs/modules/dispatcher_providers.md`
  - evidence log: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/verify_repo.log`
- Failure-chain summary:
  - trigger: acceptance gate execution on current dirty worktree
  - failing gate: `patch_check (scope from PLAN)`
  - failing check: changed file outside `artifacts/PLAN.md` `Scope-Allow`
  - consequence: verify stops before downstream gates (`behavior_catalog_check`, `contract_checks`, `doc_index_check`, `lite replay`, `python unit tests`)
- Minimal repair strategy (scoped only to first failure):
  - either add `specs/` (or exact modified specs files) to `artifacts/PLAN.md` `Scope-Allow`, or remove those files from pending patch scope; then rerun `scripts/verify_repo.ps1`.

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- External run dir:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427`
- Evidence chain:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/TRACE.md`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/artifacts/verify_report.json`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/out/scorecard.json`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/v2p_user_sim_20260226-155427/out/eval.json`

