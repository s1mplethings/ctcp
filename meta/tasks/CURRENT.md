# Task - Local Librarian Knowledge-Pack Enrichment

## Queue Binding

- Queue Item: `ADHOC-20260508-local-librarian-knowledge-pack`
- Layer/Priority: `L1 / P1`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user clarified the local librarian is mainly for maintaining local knowledge and reducing API usage.
- Lane: Delivery Lane.
- Scope boundary: enrich librarian context packs as compact local knowledge evidence; do not let librarian assign implementation tasks or create project-specific templates.

## Task Truth Source

- task_purpose:
  - Local librarian should produce API-efficient context packs from local knowledge.
  - Context packs should include compact role/usefulness metadata so planner/source-generation can consume less raw text.
  - Librarian remains a context provider, not the owner of project task assignment.
- allowed_behavior_change:
  - `context_pack.json` may include optional per-file metadata and a top-level knowledge summary.
  - Existing `files[].path/why/content` contract remains compatible.
- forbidden_goal_shift:
  - Do not add concrete project templates.
  - Do not move planner/Virtual Team task assignment into librarian.
  - Do not call external API from librarian.
  - Do not change provider credentials or endpoint config.
- in_scope_modules:
  - `tools/librarian_context_pack.py`
  - `tests/test_local_librarian.py`
  - `specs/ctcp_context_pack_v1.json`
  - `specs/modules/librarian_context_pack.md`
  - `artifacts/PLAN.md`
  - repo task/report metadata
- out_of_scope_modules:
  - source_generation implementation
  - Telegram/support bot runtime
  - provider routing and credentials
  - generated project runs
- completion_evidence:
  - focused local librarian tests pass.
  - workflow/code-health/canonical verify pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/librarian_context_pack.py`
  - `tests/test_local_librarian.py`
  - `specs/ctcp_context_pack_v1.json`
  - `specs/modules/librarian_context_pack.md`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-local-librarian-knowledge-pack.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-local-librarian-knowledge-pack.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories under repo
  - local API/proxy secrets
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no local project template fallback
  - no planner/task-assignment migration into librarian
  - no external API calls from librarian
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m py_compile tools\librarian_context_pack.py tests\test_local_librarian.py`
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_local_librarian.py" -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Current librarian already:
  - consumes `artifacts/file_request.json`
  - includes mandatory contract files
  - infers sparse local context through repo search
  - writes `summary`, `selection_strategy`, `files`, and `omitted`
- Current gap:
  - `files[]` entries carry raw content and a broad `why`, but not compact downstream-use metadata.
  - API consumers still need to infer whether a file is product context, architecture, implementation, validation, delivery, or contract.
  - The context pack does not explicitly state that librarian guidance is evidence-only and not task assignment.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: Chair/Planner writes `artifacts/file_request.json`.
- current_module: `scripts/ctcp_librarian.py` calls `build_context_pack`.
- downstream: planner/source_generation consume `artifacts/context_pack.json`.
- source_of_truth: `context_pack.json` and focused tests.
- fallback: invalid/missing request still writes explicit `context_pack.failure.json`.
- acceptance_test:
  - `tests/test_local_librarian.py`
  - workflow/module/code-health/canonical verify
- forbidden_bypass:
  - no API calls
  - no project templates
  - no task assignment from librarian
- user_visible_effect: future API prompts can receive a smaller, better labeled local knowledge pack, reducing unnecessary token usage while preserving planner ownership.

## DoD Mapping

- [x] DoD-1: `context_pack.files[]` includes role/usefulness metadata.
- [x] DoD-2: `context_pack.knowledge_summary` records compact consumption guidance and non-assignment boundary.
- [x] DoD-3: Regression tests prove sparse local knowledge requests expose this metadata.
- [x] DoD-4: Focused tests and canonical verify pass or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Existing librarian already infers sparse local context but emits mostly raw text plus broad `why`.
  - Focused tests should prove the metadata helps downstream consumers select useful context without reading everything.
- contrast:
  - A local knowledge pack is not a project plan and must not assign implementation tasks to agents.
  - API-token reduction should come from role/usefulness metadata and compact guidance, not from hard-coded project content.
- fix:
  - Add per-file metadata and top-level knowledge summary.
  - Keep planner/Virtual Team ownership of task assignment explicit in the contract/spec.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: `scripts/ctcp_librarian.py` reaches `build_context_pack`.
- accumulated: role/usefulness metadata and `knowledge_summary` are written into `context_pack.json`.
- consumed: downstream planner/source-generation can consume `context_pack.files` while using metadata to reduce raw API context.

## Issue Memory Decision Evidence

- issue_memory_decision: not required, because this is a proactive quality improvement rather than a repeated observed defect.

## Plan

1. Bind task and allowed write scope.
2. Add local-only context file classification and compact metadata.
3. Update context-pack schema/spec docs for optional metadata fields.
4. Add focused regression tests.
5. Run focused tests, workflow checks, code-health, and canonical verify.
6. Archive report/task and keep worktree clean if possible.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed.
- [x] Librarian knowledge-pack metadata implemented.
- [x] Focused tests pass.
- [x] Code-health check passes.
- [x] Canonical verify pass or first failure recorded.

## Notes / Decisions

- Default choice made: librarian provides evidence and compression hints; planner/Virtual Team still owns project task assignment.
- Skill decision: skillized: no, because this extends an existing runtime component rather than creating a reusable external workflow.
- persona_lab_impact: none.

## Results

- `context_pack.files[]` now includes `role_hint`, `relevance_summary`, `compression_hint`, `must_follow_rules`, and `avoid_patterns`.
- `context_pack.knowledge_summary` records API-use guidance and boundary `evidence_only_not_task_assignment`.
- Context-pack schema/spec docs now document optional knowledge-pack metadata.
- Focused local librarian tests pass with 9 tests OK.
- Canonical code-profile verify passed with `CTCP_FORCE_PROVIDER` cleared, `CTCP_RUNS_ROOT` set to temp, and `CTCP_SKIP_LITE_REPLAY=1`; SimLab lite was skipped because direct lite replay hung in the current environment.
