# Modules Index

Authoritative module map for CTCP execution flow.
Contract precedence remains `docs/00_CORE.md`.

## Execution Modules

| Module | Purpose | Inputs / Outputs | Dependencies | Spec |
|---|---|---|---|---|
| Orchestrator | Drive artifact-state progression and gates. | In: run artifacts + reviews; Out: `RUN.json`, `events.jsonl`, verify/failure transitions. | Core contract, run-path contract. | [specs/modules/orchestrator.md](../specs/modules/orchestrator.md) |
| Dispatcher / Providers | Route blocked artifacts to local/manual role actions. | In: gate state + `dispatch_config`; Out: outbox prompts, local execution events. | Orchestrator, role contracts. | [specs/modules/dispatcher_providers.md](../specs/modules/dispatcher_providers.md) |
| Librarian / Context Pack | Convert `file_request` into budgeted `context_pack`. | In: `artifacts/file_request.json`; Out: `artifacts/context_pack.json`. | Chair file_request and budget policy. | [specs/modules/librarian_context_pack.md](../specs/modules/librarian_context_pack.md) |
| SimLab | Replay scenarios as deterministic regression evidence. | In: scenario docs; Out: trace, scenario summary, bundles on failure. | Verify entrypoint and scenario contracts. | [specs/modules/simlab.md](../specs/modules/simlab.md) |
| Verify Repo / Quality Gates | Repository-level acceptance gate. | In: repo state + task contract; Out: pass/fail gate decision. | workflow checks, contract checks, doc-index check. | [specs/modules/verify_repo_quality_gates.md](../specs/modules/verify_repo_quality_gates.md) |
| Workflow Registry / Resolver | Resolver-first workflow selection authority. | In: goal + `workflow_registry`; Out: `artifacts/find_result.json`. | Local registry/history and contract boundary. | [specs/modules/workflow_registry_resolver.md](../specs/modules/workflow_registry_resolver.md) |
| Externals Pack / Research | Candidate-only external evidence intake. | In: guardrails + web constraints; Out: `artifacts/find_web.json` or externals pack. | Resolver-first boundary; web constraints. | [specs/modules/externals_pack_research.md](../specs/modules/externals_pack_research.md) |

## Legacy/Supporting Engine Modules

| Module | Purpose | Inputs / Outputs | Dependencies | Spec |
|---|---|---|---|---|
| ProjectScanner | Scan project files into a model input set. | In: repo tree; Out: scanned project metadata. | Core scanner conventions. | [specs/modules/project_scanner/spec.md](../specs/modules/project_scanner/spec.md) |
| GraphBuilder | Build graph structure for visualization/pipeline metadata. | In: scanner/meta outputs; Out: graph contract outputs. | ProjectScanner + MetaStore. | [specs/modules/graph_builder/spec.md](../specs/modules/graph_builder/spec.md) |
| MetaStore | Persist and expose pipeline metadata. | In: runtime/module metadata; Out: meta graph artifacts. | GraphBuilder consumers. | [specs/modules/meta_store/spec.md](../specs/modules/meta_store/spec.md) |
| RunLoader | Load and normalize run/event artifacts. | In: run directories + JSONL events; Out: run view model. | External run-dir contract. | [specs/modules/run_loader/spec.md](../specs/modules/run_loader/spec.md) |
| QWebChannel Bridge | Bridge native/runtime data to web view layer. | In: native model events; Out: bridged web channel payloads. | Web renderer. | [specs/modules/qwebchannel_bridge/spec.md](../specs/modules/qwebchannel_bridge/spec.md) |
| Web Renderer | Render graph and run views. | In: graph/meta/run data; Out: UI/web representation. | Bridge + frontend assets. | [specs/modules/web_renderer/spec.md](../specs/modules/web_renderer/spec.md) |

## Authoring Template

- Module analysis template: [specs/modules/_template.md](../specs/modules/_template.md)
