---
name: ctcp-run-report
description: Produce an auditable CTCP run report with command trace, return codes, first failure point, and minimal repair strategy.
---

# ctcp-run-report

## When To Use
- User asks for structured run summary after execution/verify.
- Need to finalize artifacts into a report-ready closure note.
- When invoked explicitly with `$ctcp-run-report`.

## When Not To Use
- No commands or gate results are available to report.
- User asks to execute workflow rather than summarize it.

## Required Readlist
- `AGENTS.md`
- `meta/reports/LAST.md` (if present)
- `meta/run_pointers/LAST_RUN.txt` (if present)
- `${run_dir}/TRACE.md` (if available)
- `${run_dir}/events.jsonl` (if available)
- `${run_dir}/artifacts/verify_report.json` (if available)

## Fixed Order
1. Locate latest run pointer and report targets.
2. Collect command trace and return codes.
3. Identify first failure point or final pass condition.
4. Summarize smallest repair plan for first failure (if any).
5. Update report with evidence paths and reproducible commands.

## Output Discipline
- Must include command list and return codes.
- Must include first failure point (or explicit PASS).
- Must include evidence file paths used.
- Must include minimal next-step fix strategy.
- Must avoid speculative conclusions unsupported by logs.
