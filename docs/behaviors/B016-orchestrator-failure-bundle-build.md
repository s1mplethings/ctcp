# B016 orchestrator-failure-bundle-build

## Reason
- Build auditable failure bundle when verify/apply fails.

## Behavior
- Trigger: Orchestrator calls make_failure_bundle on failure flows.
- Inputs / Outputs: run_dir artifacts/reviews/outbox -> failure_bundle.zip.
- Invariants: Bundle must include required evidence placeholders when files are absent.

## Result
- Acceptance: Failure bundle always contains auditable minimum entries.
- Evidence: scripts/ctcp_orchestrate.py
- Related Gates: workflow_gate

