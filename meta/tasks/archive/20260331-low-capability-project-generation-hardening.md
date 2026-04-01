# Task - low-capability-project-generation-hardening

## Queue Binding

- Queue Item: `ADHOC-20260331-low-capability-project-generation-hardening`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: User requires hard contract upgrades so project generation reliably delivers complete project repositories, not partial code/report output.
- Dependency check: `N/A (direct user request, no blocking dependency)`
- Scope boundary: Contract/docs/template hardening only for project-generation flow, output interfaces, and completion criteria.

## Task Truth Source (single source for current task)

- task_purpose: Introduce low-capability-model-friendly project generation contracts that force complete repository delivery across source/docs/workflow layers.
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/archive/20260331-shared-state-workspace-front-runtime-boundary.md`
  - `meta/reports/archive/20260331-low-capability-project-generation-hardening.md`
  - `docs/04_execution_flow.md`
  - `docs/03_quality_gates.md`
  - `docs/30_artifact_contracts.md`
  - `docs/40_reference_project.md`
  - `docs/backend_interface_contract.md`
  - `docs/shared_state_contract.md`
  - `docs/frontend_runtime_boundary.md`
  - `docs/13_contracts_index.md`
  - `docs/41_low_capability_project_generation.md`
  - `meta/templates/project_output_contract_template.json`
  - `meta/templates/project_manifest_template.json`
  - `meta/templates/project_generation_acceptance_checklist.md`
  - `meta/templates/project_assumptions_template.md`
  - `README.md` (doc index sync only)
- forbidden_goal_shift: No unrelated runtime logic refactor, no support dialogue redesign, no non-contract feature work.
- in_scope_modules:
  - `docs/`
  - `meta/`
  - `README.md`
- out_of_scope_modules:
  - `apps/`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `frontend/`
  - `tests/` (unless strictly needed for gate alignment)
- completion_evidence: Fixed generation stages + output freeze contract + project manifest/interface requirements + hard DONE criteria are all codified in authoritative docs/templates.

## Analysis / Find (before plan)

- Entrypoint analysis: Project generation policy currently spreads across `docs/04_execution_flow.md`, `docs/30_artifact_contracts.md`, and `docs/40_reference_project.md` without one hard low-capability workflow.
- Downstream consumer analysis: Frontdesk/support/backend interfaces consume project/run artifacts through bridge/API contracts and need strict manifest readability.
- Source of truth: `docs/00_CORE.md` runtime truth boundary + routed contract docs (`docs/03`, `docs/04`, `docs/30`, `docs/40`, `docs/backend_interface_contract.md`, `docs/shared_state_contract.md`).
- Current break point / missing wiring: Existing contracts allow verify-pass/report-complete outcomes without forcing complete source/docs/workflow project artifacts and manifest-level completeness proof.
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `scripts/ctcp_orchestrate.py scaffold|scaffold-pointcloud` and frontend/backend bridge result-delivery path.
- current_module: Project generation contract docs and templates.
- downstream: Backend artifact interfaces, frontdesk runtime boundary rendering, and verification gate completion decisions.
- source_of_truth: Project output contracts (`docs/30`, `docs/40`, new low-capability generation doc), backend/shared-state contracts, and task/report evidence.
- fallback: For incomplete implementations, enforce minimum closed-loop project output and explicit missing-file list instead of optimistic done.
- acceptance_test:
  - `python scripts/sync_doc_links.py --check`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
- forbidden_bypass:
  - No DONE claim from report/trace only.
  - No cross-stage generation before output contract freeze.
  - No frontdesk/support completion inference without manifest-backed artifact completeness.
- user_visible_effect: Generated project outputs become stable, enumerable, and readable via formal interfaces, including images and workflow files.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Project generation flow is fixed to one narrow 10-stage path with explicit stage input/output, output-contract freeze before generation, and mandatory stage self-checks
- [x] DoD-2: Final project output contract requires Source + Documentation + Agent Workflow layers, enforces minimum closed-loop delivery, and forbids report-only completion
- [x] DoD-3: Backend/output contracts require formal artifact interfaces including list/meta/read plus project manifest retrieval, and DONE depends on artifact completeness and readable manifests

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed (or explicitly "Docs-only, no code dirs touched")
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind ADHOC task and archive previous task card/report topic.
2) Add one authoritative low-capability project-generation workflow contract doc with fixed stages and hard done gate.
3) Update artifact, reference-project, backend-interface, shared-state, runtime-boundary, and quality-gate contracts to align with complete-project output requirements.
4) Add template assets for output contract, project manifest, assumptions, and acceptance checklist.
5) Update contract index and run doc-index sync.
6) Execute canonical verify entrypoint with `contract` profile and record first failure + minimal fix strategy if any.
7) Update report archive and `meta/reports/LAST.md` with final evidence.
8) Completion criteria: prove `connected + accumulated + consumed` for contract path.

## Check / Contrast / Fix Loop Evidence

- check-1: Existing contracts define many run artifacts but do not hard-require final project three-layer completeness.
- contrast-1: Target requires source/docs/workflow completeness plus formal interface-readable manifests and images.
- fix-1: Add explicit Final Project Output Contract and Project Manifest Contract across workflow/artifact/backend/shared-state/quality-gate docs.
- check-2: Existing reference project mode emphasizes source-mode (`template|live-reference`) but not explicit structure/workflow/docs reference styles for weak-model stability.
- contrast-2: Target requires formal `reference_project_mode` variants and structure-style proof in manifest.
- fix-2: Extend reference-project contract with style modes and manifest reflection fields.

## Completion Criteria Evidence

- completion criteria: `connected + accumulated + consumed` evidence is recorded and verified.
- connected: workflow/quality/artifact/backend/shared-state/frontend contracts point to the same project-output completeness authority.
- accumulated: templates and manifest contracts force explicit target/generated/missing/acceptance file lists.
- consumed: DONE and ResultEvent requirements consume manifest/artifact interfaces rather than report-only indicators.

## Notes / Decisions

- Default choices made: Add one new authority doc (`docs/41_low_capability_project_generation.md`) and keep most upgrades in existing routed contracts.
- Alternatives considered: Modify runtime code first; rejected for this scoped request because user asked MD/contract/flow hardening priority.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision: No new runtime bug symptom; this task is contract hardening and does not introduce a new issue-memory entry.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because` this patch updates repository-level contracts rather than introducing a reusable runtime workflow implementation.

## Results

- Files changed:
  - `README.md`
  - `docs/03_quality_gates.md`
  - `docs/04_execution_flow.md`
  - `docs/13_contracts_index.md`
  - `docs/30_artifact_contracts.md`
  - `docs/40_reference_project.md`
  - `docs/41_low_capability_project_generation.md`
  - `docs/backend_interface_contract.md`
  - `docs/frontend_runtime_boundary.md`
  - `docs/shared_state_contract.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260331-shared-state-workspace-front-runtime-boundary.md`
  - `meta/templates/project_assumptions_template.md`
  - `meta/templates/project_generation_acceptance_checklist.md`
  - `meta/templates/project_manifest_template.json`
  - `meta/templates/project_output_contract_template.json`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260331-low-capability-project-generation-hardening.md`
- Verification summary: `python scripts/workflow_checks.py`, `python scripts/sync_doc_links.py --check`, and `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` all passed.
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
