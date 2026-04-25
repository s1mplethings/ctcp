# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-23`
- Topic: `dialogue entry routing and binding fix for rough-goal domain-lift requests`
- Mode: `Support routing/binding repair`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
- `frontend/conversation_mode_router.py`
- `scripts/ctcp_support_bot.py`
- `scripts/resolve_workflow.py`
- `scripts/project_generation_gate.py`
- `tools/providers/project_generation_decisions.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_workflow_dispatch.py`

### Plan
1. Bind the dialogue entry routing/binding repair task and archive the previous dialogue-only review topic.
2. Patch support conversation classification, binding-required reply guardrails, and workflow selection heuristics.
3. Add focused regressions for this request family.
4. Run focused tests, workflow checks, and one real stdin support dialogue validation.
5. Record commands, first failure point if any, and the repaired routing/binding verdict.

### Changes
- Bound `ADHOC-20260423-dialogue-entry-routing-and-binding-fix` in `meta/tasks/CURRENT.md`.
- Archived the previous dialogue-driven review topic.
- Repaired composite dialogue classification in `frontend/conversation_mode_router.py` so task-binding plus domain-lift plus rerun requests are promoted to `PROJECT_DETAIL` before `STATUS_QUERY`.
- Repaired support-side routing/binding truth in `scripts/ctcp_support_bot.py`:
  - unbound `STATUS_QUERY` results are promoted to `PROJECT_DETAIL` for this request family
  - fresh run binding now writes `active_goal`, `active_task_id`, and `active_run_id` alongside `bound_run_id` / `bound_run_dir`
  - reply text that claims execution without real binding now degrades to an explicit `NEEDS_BINDING` message
- Strengthened project-generation goal detection in `scripts/resolve_workflow.py` and `tools/providers/project_generation_artifacts.py` for task-binding plus domain-lift plus rerun goals.
- Added focused regressions in `tests/test_runtime_wiring_contract.py`, `tests/test_support_bot_humanization.py`, and `tests/test_workflow_dispatch.py`.

### Verify
- PASS: `python -m unittest discover -s tests -p "test_workflow_dispatch.py" -v`
- PASS: `$env:CTCP_RUNS_ROOT=%TEMP%\ctcp_runs; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
- PASS: `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
- PASS: `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
- PASS: `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
- PASS: real dialogue validation
  - command: `$env:CTCP_RUNS_ROOT=%TEMP%\ctcp_runs; @'<goal>'@ | python scripts/ctcp_support_bot.py --stdin --chat-id indie-domain-lift-routing-fix-20260423`
  - result: session state persisted `latest_conversation_mode=PROJECT_DETAIL`, non-empty `active_goal`, non-empty `bound_run_id`, non-empty `bound_run_dir`
  - bound run `%TEMP%\ctcp_runs\ctcp\20260423-180633-719407-orchestrate\artifacts\find_result.json` selected `wf_project_generation_manifest`
- PASS: `python scripts/workflow_checks.py`
- FAIL: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`
  - first failure point: module protection check against pre-existing unrelated dirty/frozen-kernel files outside this task write scope
  - minimal fix strategy: re-run from a clean worktree or rebind with explicit elevation/allowed paths for those unrelated files before expecting canonical doc-only green
- triplet runtime wiring command evidence: PASS via `$env:CTCP_RUNS_ROOT=%TEMP%\ctcp_runs; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
- triplet issue memory command evidence: PASS via `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
- triplet skill consumption command evidence: PASS via `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

### Questions
- None.

### Demo
- Real validation session path: `%TEMP%\ctcp_runs\ctcp\support_sessions\indie-domain-lift-routing-fix-20260423`
- Real validation bound run path: `%TEMP%\ctcp_runs\ctcp\20260423-180633-719407-orchestrate`
- Real support reply:
  - `Current phase: 执行推进. Completed so far: 我这边已经接手到后台流程; 资料检索已完成; 需求分析已完成. Visible checkpoint: this run already has a visible checkpoint. Current blocker: the request brief has not landed yet. Next step: retry the request-brief synthesis and confirm it is generated.`
- Verified binding truth:
  - `active_goal` non-empty
  - `bound_run_id = 20260423-180633-719407-orchestrate`
  - `bound_run_dir` non-empty
  - `latest_conversation_mode = PROJECT_DETAIL`
- Verified lane selection:
  - `selected_workflow_id = wf_project_generation_manifest`
  - `decision.project_generation_goal = true`
- Current repair verdict: `PARTIAL`
- Remaining repo-level closure item:
  - canonical doc-only verify is still blocked by unrelated dirty/frozen-kernel files already present in the shared worktree
- Skill decision (`skillized: yes`): used `ctcp-workflow` for scoped execution, verification, and report closure.
