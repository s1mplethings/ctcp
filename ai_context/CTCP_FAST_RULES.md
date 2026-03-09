# CTCP Fast Rules (Hard)

1. DoD gate entrypoint is only `scripts/verify_repo.ps1` (Windows) or `scripts/verify_repo.sh` (Unix).
2. Final chat/console output must be patch-only unified diff; no report body in output.
3. Report body must be written to `meta/reports/LAST.md`.
4. Canonical verify artifact is `artifacts/verify_report.json` in external `run_dir` (`TRACE.md` + related artifacts).
5. `proof.json` is deprecated and non-authoritative; `verify_report.md` is optional human-readable material only.
6. Proceed by default; only ask when blocked by credentials/permissions, mutually exclusive decisions, or missing critical constraints.
7. Execution order is fixed and mandatory; canonical source is `docs/04_execution_flow.md` (do not redefine locally).
