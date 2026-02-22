# B018 dispatch-step-context-pack

## Reason
- Map context pack blocking state to librarian request.

## Behavior
- Trigger: Dispatch derive_request inspects missing context_pack path.
- Inputs / Outputs: blocked context_pack gate -> librarian/context_pack request.
- Invariants: Context pack request remains read-only and run_dir scoped.

## Result
- Acceptance: Blocked context pack always routes to librarian role.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

