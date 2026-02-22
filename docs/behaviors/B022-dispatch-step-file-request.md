# B022 dispatch-step-file-request

## Reason
- Map missing file request state to chair file_request action.

## Behavior
- Trigger: Dispatch derive_request inspects file_request.json path.
- Inputs / Outputs: blocked file request gate -> chair/file_request request.
- Invariants: File request target path must stay artifacts/file_request.json.

## Result
- Acceptance: File request blocking state routes to chair role.
- Evidence: scripts/ctcp_dispatch.py
- Related Gates: workflow_gate

