# B013 adlc-run-cli-entry

## Reason
- Headless ADLC bootstrap entry for doc-plan-patch-verify loop.

## Behavior
- Trigger: CLI execution of scripts/adlc_run.py.
- Inputs / Outputs: goal and verify command config -> external run_dir artifacts and trace.
- Invariants: Run artifacts are written to run_dir, not repository source tree.

## Result
- Acceptance: adlc_run returns non-zero on step failures and emits failure bundle.
- Evidence: scripts/adlc_run.py
- Related Gates: workflow_gate

