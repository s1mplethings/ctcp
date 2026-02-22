# B031 api-agent-provider-execute

## Reason
- Execute external/API agent provider with evidence pack and logs.

## Behavior
- Trigger: Dispatcher selects api_agent provider.
- Inputs / Outputs: request + evidence pack + command templates -> run_dir artifact output.
- Invariants: Patch targets must emit unified diff starting with diff --git.

## Result
- Acceptance: api_agent returns exec_failed on command failure or invalid output.
- Evidence: tools/providers/api_agent.py
- Related Gates: workflow_gate

