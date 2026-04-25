# Task - dialogue entry routing and binding fix for rough-goal domain-lift requests

## Queue Binding

- Queue Item: `ADHOC-20260423-dialogue-entry-routing-and-binding-fix`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user wants the dialogue entry and task binding repaired so rough-goal domain-lift rerun requests become real executable tasks instead of fake progress/status turns.
- Lane: Delivery Lane for entry routing / binding repair on the support and workflow mainline.
- Scope boundary: repair support conversation-mode classification, real run-binding truth, and workflow selection for this request family; do not expand product-domain implementation itself.

## Task Truth Source (single source for current task)

 - task_purpose:
  - repair support dialogue entry classification for task-binding plus rough-goal plus domain-lift/rerun requests
  - enforce that execution-claim replies require real binding fields (`active_goal`, `bound_run_id`, `bound_run_dir`) or degrade to explicit unbound/blocking language
  - strengthen lane/workflow selection so these requests default to project-generation / domain-lift repair flow instead of `STATUS_QUERY` or `wf_orchestrator_only`
 - routed_bug_class:
  - session 1 misrouted the Domain Lift request to `wf_orchestrator_only`
  - session 2 classified a stronger fresh request as `STATUS_QUERY`
  - support reply text could still claim work had started even when no run was bound
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `frontend/conversation_mode_router.py`
  - `scripts/resolve_workflow.py`
  - `scripts/project_generation_gate.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_workflow_dispatch.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
  - external support session artifacts under `%TEMP%\ctcp_runs\ctcp\support_sessions\`
  - external bound run artifacts under `%TEMP%\ctcp_runs\ctcp\`
- forbidden_goal_shift:
  - do not repair or extend the Indie Studio Hub product implementation itself
  - do not convert this into product-domain or artifact-coverage work
  - do not fake task binding or claim execution when state is still unbound
- in_scope_modules:
  - support-bot stdin conversation path
  - frontend conversation mode routing
  - workflow resolution for project-generation requests
  - session state binding truth and reply guardrails
  - focused regression tests and one real dialogue validation
- out_of_scope_modules:
  - Domain Lift business/product implementation
  - unrelated cleanup of the dirty repo worktree
  - broader support UX rewrites outside routing/binding truth
- completion_evidence:
  - targeted tests prove the request family no longer routes to `STATUS_QUERY`
  - support reply claiming execution is blocked or downgraded when binding fields are missing
  - workflow resolution proves the repaired goal no longer selects `wf_orchestrator_only`
  - one real stdin support dialogue binds a real run with non-empty goal/run fields
  - `meta/reports/LAST.md` records commands, first failure if any, and the real dialogue validation result

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `scripts/ctcp_support_bot.py`
  - `frontend/conversation_mode_router.py`
  - `scripts/resolve_workflow.py`
  - `scripts/project_generation_gate.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_workflow_dispatch.py`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
  - external support session artifacts under `%TEMP%\ctcp_runs\ctcp\support_sessions\`
  - external bound run artifacts under `%TEMP%\ctcp_runs\ctcp\`
- Protected Paths:
  - repo implementation files for Indie Studio Hub product-domain expansion itself
  - frozen-kernel files
  - unrelated dirty files outside this dialogue-test scope
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `N/A`
- Forbidden Bypass:
  - no product-domain implementation changes
  - no bypassing real run binding with reply-only text
  - no fabricated validation result
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_workflow_dispatch.py" -v`
  - `python scripts/ctcp_support_bot.py --stdin --chat-id <fixed_id>`
  - artifact inspection for `artifacts/support_reply.json`, `artifacts/support_session_state.json`, and the bound run
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Domain-lift plus rerun rough-goal requests no longer classify as `STATUS_QUERY`.
- [x] DoD-2: Support cannot claim task execution/start/rerun unless session state contains non-empty `active_goal`, `bound_run_id`, and `bound_run_dir`.
- [x] DoD-3: Workflow resolution and real dialogue validation show the request no longer falls to `wf_orchestrator_only` and binds a real run.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A - repo-local support entrypoint and prior task evidence sufficient`
- [x] Code changes allowed
- [x] Focused code/tests landed
- [x] Real dialogue validation executed
- [x] Final CTCP output captured
- [x] Support/bound-run artifact inspection completed
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Analysis / Find

- Source of truth:
  - `AGENTS.md`
  - `meta/tasks/CURRENT.md`
  - `scripts/ctcp_support_bot.py`
  - `frontend/conversation_mode_router.py`
  - `scripts/resolve_workflow.py`
  - `scripts/project_generation_gate.py`
  - `tools/providers/project_generation_artifacts.py`
  - `frontend/conversation_mode_router.py`
  - prior dialogue failure evidence in `meta/reports/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
- Current break point under test:
  - whether support dialogue can correctly classify, bind, and route a rough-goal Domain Lift rerun request into real execution instead of fake progress/status handling.
- Repo-local search sufficient: `yes`

## Integration Check

- upstream: user requirement to repair entry routing and binding truth for rough-goal Domain Lift rerun requests.
- current_module: support-bot dialogue entry, frontend mode routing, workflow resolver, and reply guardrail.
- downstream: support reply artifact, support session state, bound run, and workflow selection result.
- source_of_truth: actual support session/run artifacts under `%TEMP%\ctcp_runs`.
- fallback: if real dialogue validation still fails, record the first classification/binding failure point and stop there rather than widening scope.
- acceptance_test:
  - targeted unit regressions
  - support stdin dialogue with one fixed chat id
  - support session and bound-run artifact inspection
  - workflow checks and repo verify record
- forbidden_bypass:
  - no reply-only fake execution state
  - no claiming PASS if route or run binding still fails
- user_visible_effect: this request family should now bind a real run and enter the project-generation lane when asked through dialogue.

## Plan

1. Archive the completed dialogue-only failure review and bind this routing/binding repair task.
2. Patch the dialogue classifier, reply guard, and workflow resolver for rough-goal Domain Lift rerun requests.
3. Add focused regressions for misclassification, unbound execution claims, real binding, and workflow selection.
4. Run focused tests, workflow checks, and one real stdin support dialogue validation.
5. Record the real command evidence, first failure point if any, and final routing/binding verdict.

## Notes / Decisions

- Default environment choice: `%TEMP%\ctcp_runs` because `D:\ctcp_runs` is not writable in this environment.
- Skill decision (`skillized: yes`): use `ctcp-workflow` for the scoped bind -> patch -> verify -> report flow.
- Issue memory decision: treat `fake_execution_without_binding` as a reusable routing/binding defect class.
- persona_lab_impact: none.

## Check / Contrast / Fix Loop Evidence

- check: prior dialogue evidence showed one misroute to `wf_orchestrator_only` and one clean-session misclassification to `STATUS_QUERY`.
- contrast: this request family should create a real bound run, persist `active_goal`/`bound_run_id`/`bound_run_dir`, and select the project-generation workflow.
- fix: patched `frontend/conversation_mode_router.py`, `scripts/ctcp_support_bot.py`, `scripts/resolve_workflow.py`, and `tools/providers/project_generation_artifacts.py`; added focused regressions and ran one real stdin support dialogue validation.

## Completion Criteria Evidence

- completion criteria evidence: proved `connected + accumulated + consumed` for dialogue entry -> session state -> bound run -> workflow selection -> final report.
- connected: support entry now routes the request as `PROJECT_DETAIL`, binds a run, and persists session binding fields on the same turn.
- accumulated: focused regressions plus the real session `indie-domain-lift-routing-fix-20260423` preserved reply, session-state, and bound-run artifacts.
- consumed: final verdict uses the repaired support session and the bound run's `find_result.json`, not reply text alone.

## Results

- Files changed:
  - `frontend/conversation_mode_router.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/resolve_workflow.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_workflow_dispatch.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260423-indie-studio-hub-domain-lift-dialogue-test.md`
- Real validation session: `%TEMP%\ctcp_runs\ctcp\support_sessions\indie-domain-lift-routing-fix-20260423`
- Real validation bound run: `%TEMP%\ctcp_runs\ctcp\20260423-180633-719407-orchestrate`
- Real validation outcome:
  - `latest_conversation_mode = PROJECT_DETAIL`
  - `active_goal` non-empty
  - `bound_run_id = 20260423-180633-719407-orchestrate`
  - `bound_run_dir` non-empty
  - `find_result.json -> selected_workflow_id = wf_project_generation_manifest`
  - `decision.project_generation_goal = true`
- Final verdict for this task: `PARTIAL` pending canonical repo verify closure; routing, binding, and lane-selection repair are functioning for the validated request family.
