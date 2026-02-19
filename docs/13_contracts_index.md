
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
