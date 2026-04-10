# Demo Report - Archive

## Archived Report

- Date: `2026-04-08`
- Topic: `support chain breakpoint isolation`
- Archive Reason: active report replaced by reusable LLM core extraction analysis

### Summary

- The real `support -> bridge -> dispatch -> librarian/planner -> runtime truth` chain was mapped to concrete files and artifacts.
- Missing-target execution claims and stale support blocker carryover were converted into explicit, testable failure states.
- The resulting code now provides a better source base for reusable-provider extraction analysis, especially around dispatch evidence and local librarian enforcement.

### Verify Snapshot

- Focused regressions:
  - `python -m unittest discover -s tests -p "test_local_librarian.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_runtime_acceptance.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- Canonical verify:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `0`

### Handoff

- The next active topic should stay read-only on runtime code and produce a file-level extraction design for provider routing, OpenAI-compatible API access, Ollama-local access, and local repository retrieval.
