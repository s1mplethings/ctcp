# Demo Report Archive - Generation Provenance Ledger

See `meta/reports/LAST.md` for the full closeout report.

## Result

- Status: `done`
- Canonical verify: passed
- Command: `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
- SimLab run: `C:/Users/sunom/AppData/Local/Temp/ctcp_runs/ctcp/simlab_runs/20260502-004259`
- Full Python unit tests: `475` run, `4` skipped, OK

## User-Visible Evidence

New generated run artifacts now separate provider execution from file authorship:

- `provider_execution`: where the stage provider is recorded.
- `file_materialization`: which local materializer wrote final business files.
- `file_provenance[]`: per-file rows with `provider_authorship=not_claimed` for locally materialized files.
- `project_manifest`: consumes the same provenance fields.
- `outbox/AGENT_PROMPT_librarian_context_pack.md`: evidence for deterministic local librarian context-pack generation.
