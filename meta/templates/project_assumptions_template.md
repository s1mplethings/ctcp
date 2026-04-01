# Assumptions

## Required Format

For each assumption:

- `assumption_id`:
- `statement`:
- `why_needed`:
- `affected_files`:
- `risk_if_wrong`:
- `fallback_or_repair`:
- `status` (`active|validated|invalidated`):

## Exit Rule

- No hidden assumptions are allowed for required output files.
- If an assumption blocks a required file, keep the file in `missing_files` and do not mark task done.
