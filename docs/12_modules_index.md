# Modules Index

Authoritative module map for CTCP execution flow.
Contract precedence remains `docs/00_CORE.md`.

## Execution Modules

| Module | Purpose | Inputs / Outputs | Dependencies | Spec |
|---|---|---|---|---|
| Orchestrator | Drive artifact-state progression and gates. | In: run artifacts + reviews; Out: `RUN.json`, `events.jsonl`, verify/failure transitions. | Core contract, run-path contract. | [specs/modules/orchestrator.md](../specs/modules/orchestrator.md) |
| Front Bridge API | Narrow frontend-safe wrapper for orchestrator and run-artifact reads. | In: user goal/decision/upload metadata; Out: orchestrator calls + bridge status payloads. | `scripts/ctcp_orchestrate.py`, run_dir artifacts. | [frontend_bridge_contract.md](architecture/contracts/frontend_bridge_contract.md) |
| Dispatcher / Providers | Route blocked artifacts to local/manual role actions. | In: gate state + `dispatch_config`; Out: outbox prompts, local execution events. | Orchestrator, role contracts. | [specs/modules/dispatcher_providers.md](../specs/modules/dispatcher_providers.md) |
| Librarian / Context Pack | Convert `file_request` into budgeted `context_pack`. | In: `artifacts/file_request.json`; Out: `artifacts/context_pack.json`. | Chair file_request and budget policy. | [specs/modules/librarian_context_pack.md](../specs/modules/librarian_context_pack.md) |
| SimLab | Replay scenarios as deterministic regression evidence. | In: scenario docs; Out: trace, scenario summary, bundles on failure. | Verify entrypoint and scenario contracts. | [specs/modules/simlab.md](../specs/modules/simlab.md) |
| Verify Repo / Quality Gates | Repository-level acceptance gate. | In: repo state + task contract; Out: pass/fail gate decision. | workflow checks, contract checks, doc-index check. | [specs/modules/verify_repo_quality_gates.md](../specs/modules/verify_repo_quality_gates.md) |
| Workflow Registry / Resolver | Resolver-first workflow selection authority. | In: goal + `workflow_registry`; Out: `artifacts/find_result.json`. | Local registry/history and contract boundary. | [specs/modules/workflow_registry_resolver.md](../specs/modules/workflow_registry_resolver.md) |
| Externals Pack / Research | Candidate-only external evidence intake. | In: guardrails + web constraints; Out: `artifacts/find_web.json` or externals pack. | Resolver-first boundary; web constraints. | [specs/modules/externals_pack_research.md](../specs/modules/externals_pack_research.md) |

## Historical GUI-Era Module Docs

Legacy GUI/scanner/graph-render specs are retained only as deprecated historical material and are not part of the active CTCP runtime/build surface.

## Authoring Template

- Module analysis template: [specs/modules/_template.md](../specs/modules/_template.md)

