# B029 local-exec-librarian-run

## Reason
- Execute local librarian context-pack command.

## Behavior
- Trigger: Dispatcher selects local_exec for librarian context_pack.
- Inputs / Outputs: run_dir and file_request -> artifacts/context_pack.json plus logs.
- Invariants: Execution remains read-only with respect to repository code edits.

## Result
- Acceptance: local_exec librarian stage returns executed only on target existence.
- Evidence: tools/providers/local_exec.py
- Related Gates: workflow_gate

