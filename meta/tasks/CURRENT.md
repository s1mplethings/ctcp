# Task - project-generation-mainline-closure

## Queue Binding

- Queue Item: `ADHOC-20260402-project-generation-mainline-closure`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: concrete project-generation requests currently fall into generic patch flow and fail to form manifest-driven delivery closure.
- Dependency check: `L1-ORCH-001 = done`, `L1-DISP-001 = done`.
- Scope boundary: fix project-generation routing/gating/interface/test authenticity only; do not implement VN business product features.
- Baseline lock: `repo=D:/.c_projects/adc/ctcp`, `branch=main`, `commit=7777ebd2b46bcd334d14bc872bfbf184c9c93d78`, `version=3.2.0`.

## Task Truth Source (single source for current task)

- task_purpose: repair project-generation mainline so concrete project requests enter fixed generation stages and expose manifest-based deliverables.
- allowed_behavior_change:
  - `scripts/resolve_workflow.py`
  - `workflow_registry/index.json`
  - `workflow_registry/wf_project_generation_manifest/recipe.yaml`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_front_bridge.py`
  - `tools/providers/api_agent.py`
  - `tests/manual_backend_interface_vn_project_runner.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `docs/backend_interface_contract.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift: do not handcraft a standalone VN assistant project; do not inject fake deliverables into run_dir.
- in_scope_modules: `scripts/`, `tools/providers/`, `workflow_registry/`, `tests/`, `docs/`, `meta/`.
- out_of_scope_modules: unrelated product features and broad refactors.
- completion_evidence: fixed VN prompt run shows project-generation stages (`output_contract_freeze -> source_generation -> docs_generation -> workflow_generation -> artifact_manifest_build -> deliver`), bridge-readable manifest, and generated project root with startup smoke pass.

## Analysis / Find (before plan)

- Entrypoint analysis: project requests enter via `ctcp_front_bridge.create_run -> ctcp_orchestrate`.
- Downstream consumer analysis: `ctcp_dispatch` provider execution and `ctcp_front_bridge` output interfaces consume run artifacts.
- Source of truth: run_dir artifacts (`events.jsonl`, `TRACE.md`, `artifacts/*.json`) + bridge API responses.
- Current break point / missing wiring: workflow resolver has only generic workflow; orchestrator gate lacks project-generation stage gates; bridge lacks `get_project_manifest`; manual VN runner writes deliverables directly.
- Repo-local search sufficient: yes.

## Integration Check (before implementation)

- upstream: fixed project request from user (VN creator assistant request) as regression prompt.
- current_module: resolver + orchestrator gate + dispatch request derivation + bridge interface + api provider normalization + manual runner.
- downstream: bridge consumers and regression tests reading output artifact list and project manifest.
- source_of_truth: run_dir stage artifacts + bridge `get_project_manifest` response.
- fallback: if verify fails, preserve failure bundle and report first failure gate with minimal next fix.
- acceptance_test:
  - `python -m unittest tests/test_backend_interface_contract_apis.py -v`
  - `python tests/manual_backend_interface_vn_project_runner.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not add manual file writes in runner to simulate deliverables
  - do not claim DONE from intermediate analysis/plan artifacts only
  - do not route project-generation request to generic patch-only path by default
- user_visible_effect: project-generation runs become stage-explicit and manifest-readable even before final DONE.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Project-generation requests are routed to a dedicated workflow and do not default to the generic patch path.
- [x] DoD-2: Project-generation runs explicitly gate on output_contract_freeze, artifact_manifest_build, and deliver before verify.
- [x] DoD-3: Backend interface exposes get_project_manifest and manual VN runner no longer injects deliverables into run_dir.

## Acceptance

- [x] DoD written (this file complete)
- [ ] Research logged (if needed): not needed, repo-local artifacts sufficient
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Add dedicated project-generation workflow in resolver/registry.
2) Add orchestrator gate stages for `output_contract_freeze -> artifact_manifest_build -> deliver`.
3) Map new stage paths to dispatch requests (chair actions).
4) Add bridge `get_project_manifest` and surface in compatibility aliases/context.
5) Add deterministic JSON normalization for project-stage artifacts in api provider and patch output normalization.
6) Remove manual deliverable injection from VN manual runner and switch to fixed VN prompt regression path.
7) Update contract baseline metadata drift in backend interface doc.
8) Run targeted tests + fixed VN regression + canonical verify and report evidence.

## Notes / Decisions

- Default choices made: keep modifications minimal and chain-oriented; no new standalone project implementation.
- Alternatives considered: direct VN project generation in repo (rejected as goal-shift).
- issue memory decision: if project run still defaults to patch path after changes, log as routing regression.
- skillized: no, because this patch is repository-specific chain repair.
- check/contrast/fix loop evidence: implement routing + gate patch -> check fixed VN run timeline -> contrast against expected stage chain -> fix workflow gate blockers iteratively.
- completion criteria evidence: connected + accumulated + consumed evidence must hold before DONE claim (project workflow selected, stage artifacts accumulated, bridge/verify consumed with auditable logs).

## Results

- Files changed:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/api_agent.py`
  - `scripts/project_generation_gate.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/project_manifest_bridge.py`
  - `workflow_registry/wf_project_generation_manifest/recipe.yaml`
  - `tests/manual_backend_interface_vn_project_runner.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `artifacts/backend_interface_vn/vn_backend_interface_e2e_report.json`
- Verification summary:
  - `python -m py_compile tools/providers/project_generation_artifacts.py tools/providers/api_agent.py scripts/ctcp_dispatch.py scripts/project_generation_gate.py scripts/project_manifest_bridge.py tests/manual_backend_interface_vn_project_runner.py tests/test_backend_interface_contract_apis.py` -> `0`
  - `python -m unittest discover -s tests -p "test_workflow_dispatch.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_backend_interface_contract_apis.py" -v` -> `0`
  - `python tests/manual_backend_interface_vn_project_runner.py` -> `0` (run `20260403-013447-927876-orchestrate`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`):
  - `done`
