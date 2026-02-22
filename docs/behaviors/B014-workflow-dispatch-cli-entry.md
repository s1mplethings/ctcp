# B014 workflow-dispatch-cli-entry

## Reason
- Workflow selection and command dispatch entry.

## Behavior
- Trigger: CLI execution of scripts/workflow_dispatch.py.
- Inputs / Outputs: workflow id/goal/options -> selected workflow subprocess command.
- Invariants: Unsupported workflow IDs must hard-fail without fallback mutation.

## Result
- Acceptance: workflow_dispatch returns downstream workflow exit code.
- Evidence: scripts/workflow_dispatch.py
- Related Gates: workflow_gate

