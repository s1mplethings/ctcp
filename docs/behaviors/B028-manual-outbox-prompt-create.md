# B028 manual-outbox-prompt-create

## Reason
- Create deterministic outbox prompt for manual provider execution.

## Behavior
- Trigger: Dispatcher selects manual_outbox provider.
- Inputs / Outputs: request/config/budgets -> outbox/*.md prompt file.
- Invariants: Provider only writes run_dir outbox artifacts and never repo files.

## Result
- Acceptance: Manual outbox returns path of created prompt or budget status.
- Evidence: tools/providers/manual_outbox.py
- Related Gates: workflow_gate

