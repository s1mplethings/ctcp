# Update 2026-02-24 (MD contract + librarian injection + workflow gate)
- Scope: sync AGENTS/AI contract wording, add `CTCP_FAST_RULES.md`, enforce librarian mandatory contract injection, and require LAST report update on code-dir changes.
- Verify:
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1` => PASS
    - `workflow_checks: ok`
    - `patch_check: ok (changed_files=9)`
    - `lite replay: passed=17 failed=0`
    - `python unit tests: Ran 46 tests, OK (skipped=3)`
  - librarian mandatory injection checks => PASS
    - run-dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_librarian_manual_04e5e6d1de744948a1f1d4e0896e8ead`
    - normal budget result: `context_pack.json` includes `AGENTS.md`, `ai_context/00_AI_CONTRACT.md`, `ai_context/CTCP_FAST_RULES.md`, `docs/00_CORE.md`, `PATCH_README.md`
    - low budget result: non-zero with message `budget too small for mandatory contract files ... Please increase budget.max_files and budget.max_total_bytes.`

