---
name: ctcp-simlab-lite
description: Run lightweight SimLab scenario replay as a regression smoke gate and report deterministic pass/fail evidence.
---

# ctcp-simlab-lite

## When To Use
- User asks for quick regression evidence with lightweight scenario replay.
- Verify flow requires SimLab lite confirmation.
- When invoked explicitly with `$ctcp-simlab-lite`.

## When Not To Use
- User requires full heavy scenario matrix or unrelated testing.
- Repository state is not ready for any verify/replay checks.

## Required Readlist
- `AGENTS.md`
- `docs/03_quality_gates.md` (if present)
- `simlab/run.py`
- `simlab/scenarios/` (if present)

## Fixed Order
1. Select lite scenario set for current objective.
2. Run replay command in deterministic local mode.
3. Capture pass/fail summary and first failing scenario/check.
4. Correlate failure with gate class (workflow/contract/doc-index/test).
5. Report minimal fix path and next rerun command.

## Output Discipline
- Include replay command and return code.
- Include first failing scenario ID/check name.
- Keep remediation limited to first failure cause.
- Avoid broad refactors during replay triage.
