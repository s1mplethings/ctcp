# Root Expected Results Artifact

R301: Mainline rules are merged into existing formal contracts/runtime without adding new truth layers.
Acceptance: `README.md`, `docs/02_workflow.md`, `docs/03_quality_gates.md`, and `docs/architecture/contracts/run_manifest_contract.md` contain the single-entry/single-workflow/single-freeze/single-responsibility statements.
Evidence: README.md, docs/02_workflow.md, docs/03_quality_gates.md, docs/architecture/contracts/run_manifest_contract.md
Related-Gates: workflow_gate, plan_check

R302: Workflow naming is converged and old id emission is removed.
Acceptance: resolver fallback and selected workflow output use only `wf_project_generation_manifest`; no deprecated alias compatibility metadata remains in active runtime surfaces.
Evidence: workflow_registry/index.json, scripts/resolve_workflow.py, scripts/ctcp_dispatch.py, ctcp_adapters/dispatch_request_mapper.py, tools/run_manifest.py
Related-Gates: workflow_gate, patch_check

R303: Pipeline stage truth is reduced to the 8-stage formal mainline in runtime contract output + gate validation.
Acceptance: `pipeline_contract` emitted/validated as `goal -> intent -> spec -> scaffold -> core_feature -> smoke_verify -> demo_evidence -> delivery_package` and no separate capability/sample/refinement stage truth.
Evidence: tools/providers/project_generation_validation.py, scripts/project_manifest_bridge.py, scripts/project_generation_gate.py, tests/test_project_generation_artifacts.py
Related-Gates: workflow_gate, patch_check

R304: Single responsibility ledger is emitted with required accountability fields.
Acceptance: every run-manifest update writes `artifacts/run_responsibility_manifest.json` containing goal/entry/workflow/run binding/stage owners/provider+API/fallback/final producers/status split/first failure/final verdict.
Evidence: tools/run_manifest.py, tests/integration/test_mainline_run_contract.py
Related-Gates: workflow_gate, patch_check
