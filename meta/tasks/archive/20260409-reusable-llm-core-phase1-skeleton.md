# Task - reusable-llm-core-phase1-skeleton

## Queue Binding

- Queue Item: `ADHOC-20260409-reusable-llm-core-phase1-skeleton`
- Layer/Priority: `L1 / P0`
- Archive Reason: active topic replaced by runtime rehook and Telegram smoke integration on `2026-04-09`

## Topic Summary

- Purpose: extract the lowest-risk reusable seams into `llm_core` without changing CTCP runtime behavior.
- Scope stayed limited to the OpenAI-compatible client, repo retrieval helper, dispatch result contract, compatibility shims, and focused tests.
- Key outputs under the archived topic:
  - `llm_core/clients/openai_compatible.py`
  - `llm_core/retrieval/repo_search.py`
  - `llm_core/dispatch/result.py`
  - compatibility shims for legacy import paths

## Verification Snapshot

- Focused tests passed for:
  - `tests/test_llm_core_openai_compatible.py`
  - `tests/test_llm_core_repo_search.py`
  - `tests/test_llm_core_dispatch_result.py`
  - `tests/test_local_librarian.py`
  - `tests/test_openai_responses_client_resilience.py`
- Canonical verify:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`

## Handoff Note

- The next topic may split provider/router facades and switch CTCP runtime imports to the new core.
- Follow-up work must preserve the runtime chain from `ctcp_support_bot` / `ctcp_front_bridge` through `ctcp_dispatch` / `ctcp_orchestrate`.
