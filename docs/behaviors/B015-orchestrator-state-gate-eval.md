# B015 orchestrator-state-gate-eval

## Reason
- Evaluate run_dir artifacts into next orchestrator gate state.

## Behavior
- Trigger: Orchestrator advance/status loop calls current_gate.
- Inputs / Outputs: run_doc + artifacts/reviews state -> blocked/ready/fail/pass gate state.
- Invariants: State evaluation is artifact-driven and must not invent artifacts.

## Result
- Acceptance: Gate state must be deterministic for same artifact snapshot.
- Evidence: scripts/ctcp_orchestrate.py
- Related Gates: workflow_gate

