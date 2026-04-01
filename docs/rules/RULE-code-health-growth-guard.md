# RULE Code Health Growth Guard

## Purpose

Prevent the repository from creating or expanding god files, while allowing incremental decomposition instead of one-shot large refactors.

## Scope

- Applies to all code files matched by `meta/code_health/rules.json`.
- Enforced by `scripts/code_health_check.py`.
- Wired into canonical verify gate:
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`

## Health Signals

Per-file health evaluation must include all of:

- total lines
- effective code lines
- import count
- function count
- longest function length
- recent churn (`30d` and `90d` commit-touch counts)
- entrypoint overweight check
- multi-responsibility mix check

Line count alone is insufficient.

## Threshold Baseline

Current baseline thresholds live in `meta/code_health/rules.json`:

- `file_lines_warn = 600`
- `file_lines_critical = 1000`
- `entry_file_lines_warn = 450`
- `function_lines_warn = 80`
- `function_lines_critical = 140`
- `imports_warn = 35`
- `churn_90d_hot = 12`

These values are intentionally strict for entry files and intentionally softer for existing legacy debt (to support bounded migration).

## Growth Guard (Blocking Rule)

When running with `--enforce --changed-only`:

1. Oversized-file no-growth:
   - If a changed file is above `file_lines_critical`, its total lines must not increase versus baseline ref.
2. Entrypoint no-growth:
   - If a changed entrypoint file is above `entry_file_lines_warn`, its total lines must not increase versus baseline ref.
3. Longest-function no-growth:
   - If a changed file exceeds `function_lines_critical`, that file's longest function must not become longer versus baseline ref.
4. New-file hard stop:
   - A new file without baseline must not be created above critical file/function limits.

This rule blocks expansion first, then enables phased extraction.

## Multi-Responsibility Detection

A file is treated as mixed-responsibility risk when all hold:

- at least 3 responsibility categories are simultaneously present
- function count is at least 8
- effective code lines are at least 180

Responsibility categories are currently:

- orchestration
- io/network
- presentation/reply
- persistence/state
- domain/policy

Mixed-responsibility files are prioritized for decomposition planning even when they do not fail the blocking guard.

## CI Usage

Recommended blocking command:

```bash
python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task
```

Recommended reporting command:

```bash
python scripts/code_health_check.py --top 40 --output-json artifacts/code_health_report.json --output-md artifacts/code_health_report.md
```

In PR CI, `baseline-ref` should be set to merge-base with target branch.
In canonical local verify, `--scope-current-task` keeps enforcement aligned with the currently bound task card.
