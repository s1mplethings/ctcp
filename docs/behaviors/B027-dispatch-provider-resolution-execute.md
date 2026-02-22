# B027 dispatch-provider-resolution-execute

## Reason
- Resolve provider per role then execute provider action once.

## Behavior
- Trigger: Orchestrator calls ctcp_dispatch.dispatch_once.
- Inputs / Outputs: dispatch config + request -> provider execution result envelope.
- Invariants: local_exec remains restricted to librarian/contract_guardian roles.

## Result
- Acceptance: Provider resolution must be deterministic and auditable.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

