# Contracts Index（协议索引）

| Contract | Schema | Producer / Consumer |
|---|---|---|
| Graph JSON | [graph.schema.json](../specs/contract_output/graph.schema.json) | GraphBuilder → Web Renderer |
| Meta Pipeline Graph | [meta_pipeline_graph.schema.json](../specs/contract_output/meta_pipeline_graph.schema.json) | MetaStore ↔ GraphBuilder |
| Run Events JSONL | [run_events.schema.json](../specs/contract_output/run_events.schema.json) | Pipeline runtime → RunLoader → UI |
| File Request JSON | [ctcp_file_request_v1.json](../specs/ctcp_file_request_v1.json) | Chair/Planner → Local Librarian |
| Context Pack JSON | [ctcp_context_pack_v1.json](../specs/ctcp_context_pack_v1.json) | Local Librarian → Chair/Planner |
| Contract Review Spec | [ctcp_review_contract_v1.json](../specs/ctcp_review_contract_v1.json) | ContractGuardian → Orchestrator gate |
| Cost Review Spec | [ctcp_review_cost_v1.json](../specs/ctcp_review_cost_v1.json) | CostController → Orchestrator gate |
| Find Web JSON | [ctcp_find_web_v1.json](../specs/ctcp_find_web_v1.json) | Researcher (external) → Local Orchestrator |

## Frontend Gateway Contracts

| Contract | Schema | Producer / Consumer |
|---|---|---|
| [frontend_bridge_contract.md](architecture/contracts/frontend_bridge_contract.md) | Markdown contract | Frontend bridge → CTCP orchestrator + run artifacts |
| [frontend_session_contract.md](architecture/contracts/frontend_session_contract.md) | Markdown contract | Frontdesk state machine / session manager → frontend gateway adapters |

## Runtime Markdown Contracts

| Contract | Authority | Producer / Consumer |
|---|---|---|
| [11_task_progress_dialogue.md](11_task_progress_dialogue.md) | Markdown contract | Frontend/support reply renderers → user-visible task replies |
| [14_persona_test_lab.md](14_persona_test_lab.md) | Markdown contract | Persona-lab runner/judge/spec assets → isolated style regression evidence |
| [30_artifact_contracts.md](30_artifact_contracts.md) | Markdown contract | Orchestrator/test runners/support delivery → run artifacts and demo evidence |
| [40_reference_project.md](40_reference_project.md) | Markdown contract | scaffold/live-reference exporters → generated project provenance |
| [41_low_capability_project_generation.md](41_low_capability_project_generation.md) | Markdown contract | project generation pipeline → low-capability fixed stages, output freeze, completion hard gate |
| [backend_interface_contract.md](backend_interface_contract.md) | Markdown contract | backend bridge/service layer → frontend/support artifact/status interfaces |
| [shared_state_contract.md](shared_state_contract.md) | Markdown contract | runtime/frontend/support shared current/render state authority split |
| [frontend_runtime_boundary.md](frontend_runtime_boundary.md) | Markdown contract | frontdesk/support render layer → runtime truth boundary and completion wording guard |
| [42_frontend_backend_separation_contract.md](42_frontend_backend_separation_contract.md) | Markdown contract | frontend/support/BFF/backend strict boundary and render-only consumption model |

## Persona Lab Static Assets

| Contract / Asset | Authority | Producer / Consumer |
|---|---|---|
| [persona_lab/README.md](../persona_lab/README.md) | Repo-local static asset index | Persona-lab maintainers → future runners/judges |
| [persona_lab/personas/production_assistant.md](../persona_lab/personas/production_assistant.md) | Persona definition | Production assistant contract consumer |
| [persona_lab/rubrics/response_style_lint.yaml](../persona_lab/rubrics/response_style_lint.yaml) | Lint rubric | Judge layer → transcript scorer |
| [persona_lab/cases/no_mechanical_greeting.yaml](../persona_lab/cases/no_mechanical_greeting.yaml) | Regression case spec | Persona-lab runner → isolated test session |

