# Root Plan Artifact

Status: SIGNED
Scope-Allow: AGENTS.md, README.md, agents, artifacts, ctcp_adapters, docs, frontend, llm_core, meta, scripts, simlab, tests, tools, web, workflow_registry
Scope-Deny: src, include, CMakeLists.txt
Gates: workflow_gate, plan_check, patch_check, behavior_catalog_check, lite
Budgets: max_iterations=8, max_files=220, max_total_bytes=2500000
Stop: no_new_truth_layer=yes, single_responsibility_surface=yes, canonical_verify=run_to_conclusion
Behaviors: B002, B003, B004, B005, B010
Results: R301, R302, R303, R304

## Goal

Close the mainline by subtraction:

1. keep only required mainline surfaces in existing formal contracts/runtime,
2. remove or downgrade non-mainline exposure,
3. avoid any new governance layer/manual/wrapper,
4. emit one responsibility ledger artifact.

## Human Summary

1. converge workflow naming to one active id: `wf_project_generation_manifest`.
2. contract `pipeline_contract` stage truth to `Goal -> Intent -> Spec -> Scaffold -> Core Feature -> Smoke Verify -> Demo Evidence -> Delivery Package`.
3. emit `artifacts/run_responsibility_manifest.json` from runtime update path.
4. merge rule surfaces into existing docs (`README`, `docs/02_workflow.md`, `docs/03_quality_gates.md`, `docs/architecture/contracts/run_manifest_contract.md`).
5. run workflow/tests/benchmark-summarize/doc-only verify and record first failure if any.
