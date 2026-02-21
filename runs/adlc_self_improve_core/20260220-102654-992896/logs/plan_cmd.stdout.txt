# Goal
`external-self-improve-real-codex` (Round 1, `BOOTSTRAP`)

## Intent
Create the smallest auditable bootstrap update so this goal is explicitly tracked and discoverable, with no runtime/code-path behavior changes.

## Planned Changes
1. Add `docs/external-self-improve-real-codex.md`
- Capture goal, round, constraints snapshot, assumptions, and next-round action checklist.

2. Add `workflow_registry/external-self-improve-real-codex.round1.yaml`
- Register round metadata: `goal`, `round`, `label`, `status`, `verify_rc: N/A`, and minimal `next_actions`.

## Execution Rules
1. Use external PATCH command and emit unified diff starting with `diff --git`.
2. Touch only allowed paths.
3. Stay within limits:
- `max_files: 10`
- `max_added_lines: 800`
- `max_deleted_lines: 800`
- `max_total_lines: 800`

## Acceptance Steps
1. Generate patch; verify first line is `diff --git`.
2. Verify changed files are only:
- `docs/`
- `workflow_registry/`
3. Verify diff budgets using `git diff --numstat` (or equivalent) are within all caps.
4. Verify discoverability:
- `rg -n "external-self-improve-real-codex|BOOTSTRAP" docs/ workflow_registry/`
5. Mark Round 1 bootstrap complete with `verify_rc: N/A`.

## Out of Scope
- Runtime/source behavior changes in `scripts/`, `tools/`, `tests/`, or product code.
- Any change under blocked paths: `.github/`, `runs/`, `build/`, `dist/`.
- New dependencies or policy changes.
