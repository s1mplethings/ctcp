# B018 dispatch-step-context-pack

## Reason
- Map context pack blocking state to librarian request.

## Behavior
- Trigger: Dispatch `derive_request` inspects missing `artifacts/context_pack.json`.
- Inputs / Outputs: blocked `context_pack` gate -> `librarian/context_pack` request.
- Invariants:
  - Context pack request remains read-only and run_dir scoped.
  - Default provider path is deterministic local execution (`local_exec` -> `scripts/ctcp_librarian.py`).
  - Manual outbox for librarian is allowed only under explicit `mode: manual_outbox`.
  - Librarian output MUST conform to `ctcp-context-pack-v1` and `docs/30_artifact_contracts.md` B.1/B.2.

## Result
- Acceptance:
  - Blocked context pack always routes to `librarian` role.
  - `artifacts/context_pack.json` is produced deterministically from `artifacts/file_request.json`.
- Evidence:
  - scripts/ctcp_dispatch.py
  - tools/providers/local_exec.py
  - scripts/ctcp_librarian.py
  - docs/30_artifact_contracts.md (B.1/B.2)
- Related Gates: workflow_gate

