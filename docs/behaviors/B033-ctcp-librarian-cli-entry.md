# B033 ctcp-librarian-cli-entry

## Reason
- CLI entry for local librarian artifact generation.

## Behavior
- Trigger: CLI execution of scripts/ctcp_librarian.py.
- Inputs / Outputs: file_request.json -> artifacts/context_pack.json.
- Invariants: run_dir must be external to repository root.

## Result
- Acceptance: ctcp_librarian exits non-zero on contract violations.
- Evidence: scripts/ctcp_librarian.py
- Related Gates: workflow_gate

