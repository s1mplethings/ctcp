# CTCP Fast Rules (Hard)

1. DoD gate entrypoint is only `scripts/verify_repo.ps1` (Windows) or `scripts/verify_repo.sh` (Unix).
2. Final chat/console output must be patch-only unified diff; no report body in output.
3. Report body must be written to `meta/reports/LAST.md`.
4. Canonical verify artifact is `artifacts/verify_report.json` in external `run_dir` (`TRACE.md` + related artifacts).
5. `proof.json` is deprecated and non-authoritative; `verify_report.md` is optional human-readable material only.
6. Proceed by default; only ask when blocked by credentials/permissions, mutually exclusive decisions, or missing critical constraints.
7. Execution order is fixed and mandatory; canonical source is `docs/04_execution_flow.md` (do not redefine locally).
8. Verification profiles (`doc-only`, `contract`, `code`) are supported via `--Profile`/`--profile` flag, `CTCP_VERIFY_PROFILE` env, or auto-detection. Default is `code`. See `docs/00_CORE.md` §9.1 and `docs/04_execution_flow.md` Step 9.
9. Cleanup follows archive-first policy for knowledge assets; hard delete only for generated/temp artifacts. See `docs/cleanup_policy.md`.
