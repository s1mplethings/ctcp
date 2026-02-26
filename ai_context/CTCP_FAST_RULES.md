# CTCP Fast Rules (Hard)

1. DoD gate entrypoint is only `scripts/verify_repo.ps1` (Windows) or `scripts/verify_repo.sh` (Unix).
2. Final chat/console output must be patch-only unified diff; no report body in output.
3. Report body must be written to `meta/reports/LAST.md`.
4. Run evidence must be in external `run_dir` (`TRACE.md`, `artifacts/verify_report.json`, and related artifacts).
5. Proceed by default; only ask when blocked by credentials/permissions, mutually exclusive decisions, or missing critical constraints.
6. Execution order is fixed: Docs/Spec -> Gate -> Verify -> Report.
