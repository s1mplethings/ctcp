# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-23`
- Topic: `Indie Studio Hub spec-freeze domain lift and rough-goal rerun`
- Mode: `Project-generation contract repair / real support-bot rerun`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `contracts/project_domain_matrix.json`
- `contracts/project_capability_bundles.json`
- `tools/providers/project_generation_decisions.py`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_generic_archetypes.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_validation.py`
- `frontend/delivery_reply_actions.py`
- `scripts/support_public_delivery.py`
- `meta/tasks/CURRENT.md`

### Plan
1. Lift the rough-goal freeze from `team_task_pm_web` to a composite Indie Studio Hub domain.
2. Materialize a matching archetype with tasks/assets/bugs/build-release/docs surfaces.
3. Raise extended coverage and user-acceptance checks to the new domain contract.
4. Run focused regressions and one fresh support-bot rerun.
5. Close with real run evidence plus dual verdicts.

### Changes
- Added the new domain/family contract in:
  - `contracts/project_domain_matrix.json`
  - `contracts/project_capability_bundles.json`
- Repaired project-generation freeze and defaults in:
  - `tools/providers/project_generation_domain_contract.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_artifacts.py`
- Added the composite Indie Studio Hub generated archetype in:
  - `tools/providers/project_generation_generic_archetypes.py`
- Added Indie-specific extended coverage evidence and validation in:
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
- Exposed explicit `internal_runtime_status` and `user_acceptance_status` in:
  - `frontend/delivery_reply_actions.py`
  - `scripts/support_public_delivery.py`
- Updated focused regressions in:
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_support_delivery_user_visible_contract.py`
- Real rerun support session:
  - `%TEMP%\\ctcp_runs\\ctcp\\support_sessions\\indie-domain-freeze-lift-rerun2-20260423`
- Real rerun bound run:
  - `%TEMP%\\ctcp_runs\\ctcp\\20260423-195821-152521-orchestrate`

### Verify
- PASS: `python -m unittest discover -s tests -p "test_plane_lite_benchmark_regression.py" -v`
- PASS: `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
- PASS: `python -m unittest discover -s tests -p "test_support_delivery_user_visible_contract.py" -v`
- PASS: triplet runtime wiring command evidence via `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
- PASS: triplet issue memory command evidence via `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
- PASS: triplet skill consumption command evidence via `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
- PASS: `python scripts/workflow_checks.py`
- PASS: real support-bot rerun
  - command: `$env:CTCP_RUNS_ROOT=%TEMP%\\ctcp_runs; @'<rough goal>'@ | python scripts/ctcp_support_bot.py --stdin --chat-id indie-domain-freeze-lift-rerun2-20260423`
  - support session bound:
    - `active_goal` non-empty
    - `bound_run_id = 20260423-195821-152521-orchestrate`
    - `bound_run_dir` non-empty
    - `latest_conversation_mode = PROJECT_DETAIL`
- PASS: routing and execution
  - `artifacts/find_result.json -> selected_workflow_id = wf_project_generation_manifest`
  - `decision.project_generation_goal = true`
  - `RUN.json -> status = pass`
  - `artifacts/verify_report.json -> result = PASS`
- PASS: freeze/domain lift
  - `artifacts/output_contract_freeze.json` now freezes to:
    - `project_domain = indie_studio_production_hub`
    - `scaffold_family = indie_studio_hub`
    - `project_type = indie_studio_hub`
    - `project_archetype = indie_studio_hub_web`
- PASS: generated composite coverage
  - generated modules include first-class:
    - `assets.py`
    - `bugs.py`
    - `releases.py`
    - `docs_center.py`
  - generated docs include:
    - `docs/milestone_plan.md`
    - `docs/startup_guide.md`
    - `docs/replay_guide.md`
    - `docs/mid_stage_review.md`
  - screenshot coverage:
    - `10` PNG screenshots in `project_output/.../artifacts/screenshots/`
  - `artifacts/extended_coverage_ledger.json -> passed = true`
- PASS: dual verdicts
  - `artifacts/support_public_delivery.json -> internal_runtime_status = PASS`
  - `artifacts/support_public_delivery.json -> user_acceptance_status = PASS`
- FAIL: canonical repo doc-only verify in shared dirty workspace
  - command: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`
  - first failure point: `module protection check`
  - reason: unrelated pre-existing dirty/frozen-kernel files outside this task scope are still present in the shared worktree
  - minimal fix strategy: rerun in a clean worktree or rebind with explicit elevation for those unrelated changed files

### Questions
- None.

### Demo
- Real run path:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260423-195821-152521-orchestrate`
- Routing result:
  - `PROJECT_DETAIL` -> real bound run -> `wf_project_generation_manifest`
- Freeze result:
  - `indie_studio_production_hub / indie_studio_hub / indie_studio_hub / indie_studio_hub_web`
- Product-domain coverage result:
  - present: Dashboard, Project List, Project Overview, Milestone Backlog, Task Board/List/Detail, Asset Library, Asset Detail, Bug Tracker, Build / Release Center, Activity Feed, Docs Center, Project Settings
- Dedicated docs result:
  - present: `milestone_plan`, `startup_guide`, `replay_guide`, `mid_stage_review`
- Screenshot result:
  - `10` PNG screenshots
- Internal runtime status:
  - `PASS`
- User acceptance status:
  - `PASS`
- Final verdict:
  - `PASS`
