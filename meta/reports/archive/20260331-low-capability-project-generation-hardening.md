# Demo Report - 20260331 Low-Capability Project Generation Hardening

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `meta/tasks/CURRENT.md`
- `docs/04_execution_flow.md`
- `docs/30_artifact_contracts.md`
- `docs/40_reference_project.md`
- `docs/backend_interface_contract.md`
- `docs/shared_state_contract.md`
- `docs/frontend_runtime_boundary.md`
- `docs/13_contracts_index.md`

### Plan

1. Bind a dedicated ADHOC queue item for low-capability project-generation hardening.
2. Add one authoritative low-capability generation contract document with fixed stages, output freeze, and hard done gate.
3. Strengthen routed contracts (workflow, quality gates, artifacts, reference project, backend interface, shared state, frontend boundary).
4. Add templates for output contract, project manifest, assumptions, and acceptance checklist.
5. Update contract index and report/task archives.
6. Run doc index check + canonical verify (`contract` profile) and record first failure/minimal fix strategy.

### Changes

- Added `docs/41_low_capability_project_generation.md`.
- Updated `docs/04_execution_flow.md` with fixed project-generation subflow (`intake -> ... -> deliver`) and output-freeze precondition.
- Updated `docs/03_quality_gates.md` with project output completeness lint and output-freeze sequencing lint.
- Updated `docs/30_artifact_contracts.md` with final project output contract, project manifest contract, formal interface parity, and ResultEvent binding.
- Updated `docs/40_reference_project.md` with formal `reference_project_mode` variants and style-reuse boundaries.
- Reworked `docs/backend_interface_contract.md` to require `list/get-meta/read/get_project_manifest` interface set and hard done conditions.
- Updated `docs/shared_state_contract.md` to bind current/render truth and artifact completeness fields.
- Updated `docs/frontend_runtime_boundary.md` to prevent done claims without manifest-backed completeness.
- Updated `docs/13_contracts_index.md` to include new contract authorities.
- Added templates:
  - `meta/templates/project_output_contract_template.json`
  - `meta/templates/project_manifest_template.json`
  - `meta/templates/project_generation_acceptance_checklist.md`
  - `meta/templates/project_assumptions_template.md`
- Updated `meta/backlog/execution_queue.json` and rebound `meta/tasks/CURRENT.md`.
- Archived previous task card at `meta/tasks/archive/20260331-shared-state-workspace-front-runtime-boundary.md`.

### Verify

- `python scripts/workflow_checks.py` -> 1
  - first failure point: workflow gate precheck
  - first failing reason: changes detected but `meta/reports/LAST.md` was not updated.
  - minimal fix strategy: update `meta/reports/LAST.md` with this task evidence before rerunning checks.
- `python scripts/workflow_checks.py` -> 0
- `python scripts/sync_doc_links.py --check` -> 0
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract` -> 0
  - first failure point: `workflow_checks` precheck before report update
  - first failing reason: `meta/reports/LAST.md` missing update evidence.
  - minimal fix strategy: update report first, rerun workflow/verify gates.
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> profile-skip (contract profile)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> profile-skip (contract profile)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> profile-skip (contract profile)

### Questions

- None.

### Demo

- Project generation is now contractually forced to deliver full repository layers (source/docs/workflow), not report-only output.
- Completion now depends on manifest/interface readability and explicit missing-file visibility.
- Reference project reuse is formalized as structure/workflow/docs style inheritance, not business-code copy.
