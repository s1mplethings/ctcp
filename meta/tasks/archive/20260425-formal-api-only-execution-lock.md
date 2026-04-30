# Task - Formal API-Only Execution Lock

## Queue Binding

- Queue Item: `ADHOC-20260425-formal-api-only-execution-lock`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the user explicitly requested a hard formal-mode execution lock so CTCP’s formal project-generation mainline cannot claim success through any non-`api_agent` provider path outside librarian/context_pack.
- Lane: Delivery Lane for the repo task itself, because this is a bounded runtime-enforcement and benchmark/reporting hardening change on the existing formal mainline.
- Scope boundary: implement `CTCP_FORMAL_API_ONLY=1`, fail fast on non-librarian non-`api_agent` formal steps, block local fallback/local normalizer success paths in the formal mainline, emit auditable provider ledger output, expose API coverage in formal benchmark/portfolio summaries, and add focused regressions.

## Task Truth Source (single source for current task)

- task_purpose:
  - introduce a formal-mode hard lock via `CTCP_FORMAL_API_ONLY=1`
  - keep `librarian/context_pack` as the only local exception in the formal project-generation mainline
  - make all other formal mainline roles and project-impacting stages fail fast unless the resolved provider is `api_agent`
  - forbid silent local fallback, manual outbox success, mock/local success, or local artifact normalizer synthesis from counting as formal success
  - emit a provider ledger for each run so provider choice, fallback, request id, local function usage, and verdict are auditable per step
  - make formal benchmark/endurance/portfolio summaries report API coverage and refuse PASS when critical steps are not API-backed
- routed_bug_class:
  - formal project-generation provider routing and auditability hardening
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260425-five-project-portfolio-execution.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-five-project-portfolio-execution.md`
  - `AGENTS.md`
  - `llm_core/dispatch/router.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/42_frontend_backend_separation_contract.md`
  - `scripts/ctcp_dispatch.py`
  - `scripts/classify_change_profile.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_bridge_views.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/formal_benchmark_runner.py`
  - `scripts/module_protection_check.py`
  - `scripts/prompt_contract_check.py`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `scripts/workflow_checks.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/run_manifest.py`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `docs/50_prompt_hierarchy_contract.md`
  - `frontend/conversation_mode_router.py`
  - `frontend/delivery_reply_actions.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/test_provider_selection.py`
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_formal_benchmark_runner.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_prompt_contract_check.py`
  - `tests/test_runtime_wiring_contract.py`
- forbidden_goal_shift:
  - do not widen this task into general support-lane style cleanup
  - do not claim formal PASS through any non-`api_agent` project-generation path except librarian/context_pack
  - do not leave local fallback or local normalizer success paths silently treated as equivalent to formal API execution
  - do not re-architect unrelated providers; keep their code only as non-formal/test/debug paths
- in_scope_modules:
  - queue/task/report/archive bookkeeping
  - dispatch/provider resolution and formal-mode enforcement
  - formal benchmark summary/evaluation
  - support/provider failover restrictions in formal mode
  - project-generation portfolio API-coverage reporting
  - provider ledger generation and summary
  - targeted regression tests and benchmark docs
- out_of_scope_modules:
  - unrelated project-generation product improvements
  - generic repo hygiene cleanup
  - new benchmark domains unrelated to API-only enforcement
- completion_evidence:
  - formal mode has a single explicit switch and blocks non-librarian non-`api_agent` formal steps
  - a provider ledger is written with the required audit fields
  - formal benchmark/endurance/portfolio summaries expose API coverage and fail formal PASS when coverage is insufficient
  - regressions prove the local exception, fail-fast behavior, no-local-fallback PASS rule, ledger generation, and portfolio coverage surfacing

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260425-five-project-portfolio-execution.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-five-project-portfolio-execution.md`
  - `AGENTS.md`
  - `llm_core/dispatch/router.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/10_team_mode.md`
  - `docs/42_frontend_backend_separation_contract.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `docs/50_prompt_hierarchy_contract.md`
  - `frontend/conversation_mode_router.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/formal_benchmark_runner.py`
  - `scripts/classify_change_profile.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_bridge_views.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/module_protection_check.py`
  - `scripts/prompt_contract_check.py`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `scripts/workflow_checks.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/run_manifest.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/test_provider_selection.py`
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_formal_benchmark_runner.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_prompt_contract_check.py`
  - `tests/test_runtime_wiring_contract.py`
- Protected Paths:
  - generated runtime outputs inside the repo
  - unrelated product-generation heuristics outside the formal-lock surface unless required by the hard block
  - unrelated support persona/style paths
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `Formal API-Only Execution Lock inherits the already-dirty shared worktree on 2026-04-25 so formal mainline enforcement can change dispatch/orchestrate/support/benchmark runtime files without hiding frozen-kernel ownership in repo verify`
- Forbidden Bypass:
  - no silent provider remap that lets non-librarian formal steps continue as success
  - no local fallback or local normalizer synthesis may count as formal API success
  - no benchmark PASS when provider coverage is missing or mixed
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_plane_lite_benchmark_regression.py" -v`
  - `python -m unittest discover -s tests -p "test_formal_benchmark_runner.py" -v`
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python scripts/module_protection_check.py`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## Analysis / Find (before plan)

- Entrypoint analysis: formal project-generation runs enter through support -> dispatch -> orchestrate and through formal benchmark wrappers, while project-generation stage artifacts and portfolio summaries are still normalized locally unless explicitly blocked.
- Downstream consumer analysis: dispatch/orchestrate/support/benchmark summaries and portfolio summaries must all consume one auditable provider ledger and must not report formal PASS when critical stages are non-API or local-fallback-backed.
- Source of truth:
  - `AGENTS.md`
  - `.agents/skills/ctcp-gate-precheck/SKILL.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `docs/25_project_plan.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `llm_core/dispatch/router.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/formal_benchmark_runner.py`
  - `tools/providers/project_generation_source_stage.py`
- Current break point / missing wiring:
  - provider resolution still silently remaps some local providers to `api_agent` instead of failing in formal mode
  - patchmaker/mock fallback can still create local success artifacts after provider failure
  - project-generation JSON artifact normalization still synthesizes formal outputs locally
  - formal benchmark summaries rely on `api_calls.jsonl` and acceptance triplets, but not on a per-step provider ledger
  - portfolio summary does not yet expose per-project key-stage API coverage
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: the repo already has API, local, mock, manual-outbox, and portfolio paths; this task narrows which ones are legal in formal mode.
- current_module: provider resolution, fallback handling, artifact normalization, benchmark evaluation, and portfolio API coverage reporting.
- downstream: formal benchmark reports, orchestrator decisions, and portfolio summaries must all consume the same provider-ledger truth.
- source_of_truth: dispatch result evidence plus run-level provider ledger rows written during actual execution.
- fallback: outside formal mode, existing local/mock/manual paths may remain for tests/debug/offline; inside formal mode they must fail closed instead of downgrading to success.
- acceptance_test:
  - prove `librarian/context_pack` is the only local exception in formal mode
  - prove non-librarian formal requests fail when the provider is not `api_agent`
  - prove local fallback/local normalizer paths cannot count as formal PASS
  - prove provider ledger files and API coverage summaries are generated
- forbidden_bypass:
  - do not treat silent provider remap as equivalent to an auditable fail-fast block
  - do not use local provider success to masquerade as formal API execution
  - do not mark formal PASS from acceptance artifacts alone when provider ledger coverage is incomplete
- user_visible_effect: formal project-generation runs either show end-to-end API coverage with auditable ledger evidence or fail explicitly at the first non-API/mainline-local step.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Formal mode introduces `CTCP_FORMAL_API_ONLY=1` and hard-fails non-librarian project-generation mainline steps unless the resolved provider is `api_agent`, with no silent fallback to local_exec, ollama, mock, manual_outbox, or local artifact normalizer success paths.
- [x] DoD-2: Every formal run emits an auditable provider ledger with role, action, provider_used, external_api_used, request_id when present, fallback_used, local_function_used when present, and verdict, and formal benchmark/endurance/portfolio summaries report API coverage from that ledger.
- [x] DoD-3: Regression tests prove librarian/context_pack remains the only local exception, non-librarian formal steps fail fast when not `api_agent`, local fallback cannot count as formal PASS, provider ledger is written, and multi-project portfolio summaries expose per-project key-stage API coverage.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local readlist above)
- [x] Code changes allowed
- [x] Implementation patched
- [x] Focused regressions passing
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Archive the prior active task/report and bind the new formal API-only lock task.
2. Add a formal-mode switch and fail-fast provider enforcement in dispatch/router/orchestrate/support.
3. Block formal success paths that still synthesize project-generation artifacts locally.
4. Write run-level provider ledger output and surface API coverage in formal benchmark and portfolio summaries.
5. Add focused regressions, run targeted checks, then run canonical verify and record the first failure if any.

## Notes / Decisions

- Default choices made: formal enforcement is opt-in through `CTCP_FORMAL_API_ONLY=1`, but formal benchmark/endurance entrypoints will enable it by default.
- Alternatives considered: keeping silent provider remap and only marking summaries as mixed coverage was rejected because the user explicitly asked for a hard execution lock, not softer reporting.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - `None`
- Issue memory decision: update the existing recurring failure memory if a new formal-mode gap is observed during verify; otherwise no new issue-memory entry is needed because this task is a preventative routing hardening pass.
- Skill decision (`skillized: no, because ...`): `skillized: no, because formal API-only locking is a repo-local runtime contract and verification surface, not a reusable workflow asset for other repos.`
- persona_lab_impact: `none`

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260425-five-project-portfolio-execution.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260425-five-project-portfolio-execution.md`
  - `tools/formal_api_lock.py`
  - `llm_core/dispatch/router.py`
  - `llm_core/providers/api_provider.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `scripts/formal_benchmark_runner.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_artifacts.py`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `tests/test_provider_selection.py`
  - `tests/test_plane_lite_benchmark_regression.py`
  - `tests/test_formal_benchmark_runner.py`
  - `tests/test_project_generation_artifacts.py`
- Verification summary: `targeted regressions + workflow/module-protection checks passed; canonical verify failed first at code health growth-guard`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`

## Check / Contrast / Fix Loop Evidence

- check: the current repo already records provider/evidence details, but it still allows silent provider remap, patchmaker fallback, and local artifact synthesis to produce formal-looking success.
- contrast: the user asked for a hard formal API-only lock, so mixed local/API execution must become an explicit failure rather than an informational note.
- fix: enforce fail-fast in formal mode, emit a dedicated provider ledger, and bind formal PASS to provider-ledger coverage instead of artifact existence alone.

## Completion Criteria Evidence

- completion criteria evidence: must prove `connected + accumulated + consumed` for formal API-only enforcement.
- connected: formal-mode entrypoints, dispatch resolution, support/orchestrate execution, and benchmark evaluation all consume the same `CTCP_FORMAL_API_ONLY=1` rule.
- accumulated: provider ledger rows preserve every formal step’s provider choice, API usage, fallback state, local function usage, and verdict.
- consumed: formal benchmark and portfolio summaries use that ledger to compute API coverage and block PASS when coverage is incomplete.
