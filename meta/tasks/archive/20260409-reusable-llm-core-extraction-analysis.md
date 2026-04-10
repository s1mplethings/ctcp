# Task - reusable-llm-core-extraction-analysis

## Queue Binding

- Queue Item: `ADHOC-20260409-reusable-llm-core-extraction-analysis`
- Layer/Priority: `L1 / P0`
- Archive Reason: active topic replaced by reusable LLM core phase 1 skeleton extraction on `2026-04-09`

## Topic Summary

- Purpose: map the reusable LLM/provider/router/retrieval surface in CTCP and produce a file-level migration blueprint before any implementation.
- Scope stayed read-only on runtime/provider behavior and focused on real code inspection plus extraction design.
- Key outputs under the archived topic:
  - concrete remote/local provider call chains
  - reusable-vs-CTCP split with coupling points
  - minimal target package tree, migration table, and core interface proposal

## Verification Snapshot

- Canonical verify summary:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only` -> `0`

## Handoff Note

- Follow-up topic is implementation-scoped but limited to Phase 1 skeleton work only.
- The next patch may create `llm_core` clients/retrieval/result modules, focused tests, and compatibility shims.
- The next patch must not change the main behavior of `scripts/ctcp_dispatch.py`, `scripts/ctcp_orchestrate.py`, or `scripts/ctcp_support_bot.py`.
