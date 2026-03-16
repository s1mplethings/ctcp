# Task - <topic>

## Queue Binding

- Queue Item: `<Lx-XXX-000 | ADHOC-YYYYMMDD-<slug>>`
- Layer/Priority: `<Lx / Px>`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: `<one line>`
- Dependency check: `<dep id> = done|blocked`
- Scope boundary: `<one line>`

## Task Truth Source (single source for current task)

- task_purpose:
- allowed_behavior_change:
- forbidden_goal_shift:
- in_scope_modules:
- out_of_scope_modules:
- completion_evidence:

## Analysis / Find (before plan)

- Entrypoint analysis: `<one line>`
- Downstream consumer analysis: `<one line>`
- Source of truth: `<one line>`
- Current break point / missing wiring: `<one line>`
- Repo-local search sufficient: `yes/no`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream: `<one line>`
- current_module: `<one line>`
- downstream: `<one line>`
- source_of_truth: `<one line>`
- fallback: `<one line>`
- acceptance_test:
  - `<one line per command>`
- forbidden_bypass:
  - `<one line per bypass>`
- user_visible_effect: `<one line>`

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: `<copy from queue item dod[0]>`
- [ ] DoD-2: `<copy from queue item dod[1]>`
- [ ] DoD-3: `<copy from queue item dod[2] or write "Not Applicable: <reason>">`

## Acceptance (must be checkable)

- [ ] DoD written (this file complete)
- [ ] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [ ] Code changes allowed (or explicitly "Docs-only, no code dirs touched")
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Analysis/find tasks (if pending).
2) Docs/spec/meta changes first.
3) Minimal implementation changes.
4) Topic-related local checks.
5) `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
6) `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
7) `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
8) Record the first failure and minimal fix strategy.
9) Canonical verify gate: `scripts/verify_repo.*`
10) Completion criteria: prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made: `<one line>`
- Alternatives considered: `<one line>`
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - `<one line or None>`
- Issue memory decision: `<one line>`
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `<one line>`

## Results

- Files changed:
  - `<one line per file>`
- Verification summary: `<one line>`
- Queue status update suggestion (`todo/doing/done/blocked`): `<one line>`

## Minimal Example

- Queue Item: `L0-PLAN-001`
- Layer/Priority: `L0 / P0`
- Context: "Unify verify naming across docs and scripts; no product code changes."
- DoD-1: "README/doc index and contracts index aligned."
- Verify: "`python scripts/sync_doc_links.py --check` pass, `scripts/verify_repo.ps1` pass."
