# Demo Report Archive - Support Bot Slimming

See `meta/reports/LAST.md` for the full closeout report.

## Result

- `scripts/ctcp_support_bot.py`: about `6975` lines -> about `6533` lines.
- Added `scripts/ctcp_support_bot_constants.py`.
- Added `scripts/ctcp_support_bot_text_patterns.py`.
- Targeted support tests passed.
- Markdown remains report/spec metadata only.

## Canonical Verify

- Command: `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
- Result: failed at full Python unit tests after earlier gates passed.
- First failure: `tests/test_project_generation_variant_content.py::test_narrative_sample_pipeline_same_goal_uses_run_variant_content`.
- Note: the failing test passed on isolated rerun, so it is recorded as a separate project-generation variant-content flake/blocker.
