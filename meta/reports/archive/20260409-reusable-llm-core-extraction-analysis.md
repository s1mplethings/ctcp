# Demo Report - Archive

## Archived Report

- Date: `2026-04-09`
- Topic: `reusable llm core extraction analysis`
- Archive Reason: active report replaced by reusable llm core phase 1 skeleton extraction

### Summary

- Mapped the real reusable-core candidate surface to concrete files and functions.
- Confirmed the lowest remote transport is `scripts/externals/openai_responses_client.py`, the lightweight repo retrieval helper is `tools/local_librarian.py`, and the dispatch/result seam already exists in `scripts/ctcp_dispatch.py` plus `tools/dispatch_result_contract.py`.
- Identified the main CTCP coupling hotspots in `tools/providers/api_agent.py`, `tools/providers/ollama_agent.py`, and the whiteboard/gate logic inside `scripts/ctcp_dispatch.py`.

### Verify Snapshot

- Canonical verify:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only` -> `0`

### Handoff

- The next active topic should implement only the first extraction phase:
  - `llm_core/clients`
  - `llm_core/retrieval`
  - `llm_core/dispatch/result`
  - focused unit tests
  - compatibility shims
- Provider splitting, router extraction, and runtime import switching remain out of scope until the new skeleton passes focused tests.
