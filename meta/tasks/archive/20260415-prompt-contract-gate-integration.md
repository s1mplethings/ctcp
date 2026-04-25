# Task - prompt-contract-gate-integration

## Archive Note

- This archive topic records the 2026-04-15 verify-gate integration for the Virtual Team prompt-contract checker.
- The change is intentionally narrow: both verify entrypoints plus `docs/03_quality_gates.md`, with the first remaining blocker still expected to stay outside this task if root plan artifacts are missing.

## Closure Summary

- `scripts/verify_repo.ps1` now runs the prompt-contract checker before `plan_check`, and real PowerShell verify logs confirm the new gate executes successfully.
- `scripts/verify_repo.sh` was patched at the same position, but a runtime proof on this machine was blocked by a local WSL/bash environment failure before the script body.
- `docs/03_quality_gates.md` now treats the prompt-contract checker as part of the script-aligned verify sequence and as a named governance lint class.
