# Demo Report Archive - Support Bot Progress Evidence Split

See `meta/reports/LAST.md` for the full closeout report.

## Result

- `scripts/ctcp_support_bot.py`: `6192` lines -> `5828` lines.
- Added `scripts/ctcp_support_bot_progress.py` (`365` lines).
- The old progress binding path is split into smaller helper functions.
- Targeted support tests passed.
- Markdown remains report/spec metadata only.

## Canonical Verify

- Contract profile command: `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile contract`
- Result: passed.
- Code profile note: previous support-bot split code-profile verify timed out after `900` seconds with no first failing gate returned, so full code-profile PASS remains unproven.
