# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-23`
- Topic: `Indie Studio Hub Domain Lift rough-goal rerun through repaired support entry`
- Mode: `Support-entry rerun validation / product-generation audit`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/12_virtual_team_contract.md`
- `docs/30_artifact_contracts.md`
- `docs/41_low_capability_project_generation.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/archive/20260423-indie-studio-hub-generation-test.md`
- `meta/reports/archive/20260423-dialogue-entry-routing-and-binding-fix.md`

### Plan
1. Rebind from the completed support-entry repair into a new rerun-validation task.
2. Start one fresh rough-goal Domain Lift request through the real support bot entry.
3. Confirm the support session binds a real run and selects `wf_project_generation_manifest`.
4. Advance the run to completion and inspect spec-freeze, generated project, docs, screenshots, and delivery artifacts.
5. Separate internal runtime pass from user-level acceptance and close the task with the first failure point.

### Changes
- Archived the completed support-entry repair task/report into:
  - `meta/tasks/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
  - `meta/reports/archive/20260423-dialogue-entry-routing-and-binding-fix.md`
- Bound `ADHOC-20260423-indie-studio-hub-domain-lift-rerun-test` in `meta/tasks/CURRENT.md`.
- Added the new archive row to `meta/tasks/ARCHIVE_INDEX.md`.
- Created one fresh support session and bound run through the repaired dialogue entry:
  - support session: `%TEMP%\ctcp_runs\ctcp\support_sessions\indie-domain-lift-rerun-20260423`
  - bound run: `%TEMP%\ctcp_runs\ctcp\20260423-190306-801392-orchestrate`
- Advanced the bound run to completion and audited the resulting artifacts instead of changing product-generation implementation.

### Verify
- PASS: real support-bot entrypoint
  - command: `$env:CTCP_RUNS_ROOT=%TEMP%\ctcp_runs; @'<rough goal>'@ | python scripts/ctcp_support_bot.py --stdin --chat-id indie-domain-lift-rerun-20260423`
  - support session state persisted:
    - `latest_conversation_mode = PROJECT_DETAIL`
    - `active_goal` non-empty
    - `bound_run_id = 20260423-190306-801392-orchestrate`
    - `bound_run_dir` non-empty
- PASS: routing
  - `artifacts/find_result.json` selected `wf_project_generation_manifest`
  - `decision.project_generation_goal = true`
- PASS: run completion
  - command: `$env:CTCP_RUNS_ROOT=%TEMP%\ctcp_runs; python scripts/ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 20`
  - `RUN.json -> status = pass`
  - `artifacts/run_manifest.json -> final_status = pass`
  - `artifacts/verify_report.json -> result = PASS`
  - delivery artifacts present:
    - `artifacts/final_project_bundle.zip`
    - `artifacts/intermediate_evidence_bundle.zip`
    - `artifacts/support_public_delivery.json`
    - cold replay passed in `artifacts/delivery_replay/replay_artifacts/replay_report.json`
- FAIL: user-level acceptance
  - first failure point: `artifacts/output_contract_freeze.json` froze the project back to:
    - `project_domain = team_task_management`
    - `project_archetype = team_task_pm_web`
    - `required_screenshots = 8`
  - generated README title is still `Plane-lite Team PM`
  - generated docs only cover task-PM surfaces; no first-class Asset/Bug/Build-Release/Docs Center pages were generated
  - required dedicated docs missing:
    - `docs/milestone_plan.md`
    - `docs/startup_guide.md`
    - `docs/replay_guide.md`
    - `docs/mid_stage_review.md`
  - screenshot coverage still below requested bar:
    - actual screenshot image count in project output = `8` PNG screenshots
    - extra `final-ui.source.html` exists but is not a screenshot
  - minimal fix strategy:
    - raise the domain freeze so this rough-goal signal cannot collapse to `team_task_pm_web`
    - hard-gate Asset/Bug/Build-Release/Docs Center plus the four dedicated docs and `10+` screenshots at user-acceptance level
- PASS: repo workflow gate after task-card repair
  - `python scripts/workflow_checks.py`
- FAIL: canonical verify for repo doc-only profile in the shared workspace
  - command: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`
  - first failure point: `module protection check`
  - reason: unrelated pre-existing dirty/frozen-kernel files outside this task write scope are still present in the shared worktree
  - minimal fix strategy: rerun from a clean worktree, or rebind with explicit elevation/allowed paths for those unrelated changed files before expecting canonical repo green
- triplet runtime wiring command evidence: PASS via `$env:CTCP_RUNS_ROOT=%TEMP%\ctcp_runs; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
- triplet issue memory command evidence: PASS via `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
- triplet skill consumption command evidence: PASS via `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

### Questions
- None.

### Demo
- Support session path:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\support_sessions\indie-domain-lift-rerun-20260423`
- Bound run path:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260423-190306-801392-orchestrate`
- Routing result:
  - `PROJECT_DETAIL` -> bound run -> `wf_project_generation_manifest`
- Spec freeze result:
  - still collapsed to `team_task_pm_web`
  - `project_domain = team_task_management`
  - `required_screenshots = 8`
- Product-domain coverage result:
  - present: dashboard, project list/overview, task board/list/detail, activity, settings
  - absent as first-class generated domains/views: Asset Library, Asset Detail, Bug Tracker, Build / Release Center, Docs Center
  - missing dedicated docs: `milestone_plan`, `startup_guide`, `replay_guide`, `mid_stage_review`
- Internal runtime status:
  - `PASS`
- User acceptance status:
  - `NEEDS_REWORK`
- Final verdict for this rerun:
  - `NEEDS_REWORK`
