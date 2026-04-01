# Task - md-navigation-pointer-alignment

## Queue Binding

- Queue Item: `ADHOC-20260401-md-navigation-pointer-alignment`
- Layer/Priority: `L2 / P1`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: NOTES.md states MD reform goals that no longer match current AGENTS/CURRENT/LAST state.
- Dependency check: `ADHOC-20260331-frontdesk-backend-separation-render-only = done`
- Scope boundary: Docs/meta alignment only (no runtime behavior change).

## Task Truth Source (single source for current task)

- task_purpose: Align markdown navigation claims with actual files and restore thin-pointer task/report flow.
- allowed_behavior_change:
  - `AGENTS.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260401-md-navigation-pointer-alignment.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260401-md-navigation-pointer-alignment.md`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- forbidden_goal_shift: No script/runtime/frontend/backend logic edits.
- in_scope_modules:
  - `AGENTS.md`
  - `meta/`
  - `tests/fixtures/patches/`
- out_of_scope_modules:
  - `scripts/`
  - `frontend/`
  - `tests/` (except `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`)
  - `src/`
  - `include/`
  - `web/`
- completion_evidence: AGENTS TOC present, CURRENT/LAST thin pointers restored, canonical verify passes.

## Analysis / Find (before plan)

- Entrypoint analysis: Repo task/report discipline enters through `meta/tasks/CURRENT.md` + `meta/reports/LAST.md`.
- Downstream consumer analysis: Agents use these pointers for fast startup and contract-grounded execution.
- Source of truth: `AGENTS.md`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`, and their archive targets.
- Current break point / missing wiring: AGENTS TOC missing; CURRENT/LAST are no longer thin pointers as NOTES expects.
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: User request + `.agent_private/NOTES.md` owner intent.
- current_module: Agent contract + task/report pointer files.
- downstream: Faster task bootstrap and lower context load.
- source_of_truth: Queue item + task/report archive entries.
- fallback: Keep mandatory workflow fields while compressing pointer files.
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - Skip queue bind/current bind/report update
  - Remove mandatory workflow evidence fields required by workflow_checks
- user_visible_effect: MD navigation and task/report startup path become consistent and scan-friendly.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: AGENTS.md contains explicit TOC anchors for fast section jump and matches README/notes navigation claims
- [x] DoD-2: meta/tasks/CURRENT.md is reduced to a thin active-task pointer while preserving mandatory workflow evidence fields
- [x] DoD-3: meta/reports/LAST.md is reduced to a thin latest-report pointer with required read/plan/verify/demo evidence

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed (Docs-only, no code dirs touched)
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind ADHOC task and archive previous active topic.
2) Add TOC anchors to `AGENTS.md`.
3) Create task/report archive entries for this topic.
4) Replace CURRENT/LAST with thin pointers that keep required fields.
5) Run workflow check + canonical verify and update evidence.

## Check / Contrast / Fix Loop Evidence

- check-1: NOTES claims TOC in AGENTS but file has no TOC marker.
- contrast-1: Target requires explicit TOC anchors for fast jump.
- fix-1: Insert stable TOC block at top of AGENTS.
- check-2: CURRENT/LAST are larger than thin-pointer intent.
- contrast-2: Target requires pointer-first files with archive detail.
- fix-2: Move details to archive entries and keep thin pointers in CURRENT/LAST.

## Completion Criteria Evidence

- completion criteria: `connected + accumulated + consumed`.
- connected: Queue/task/report pointers consistently reference active archive entries.
- accumulated: Archive entries preserve full task/report evidence.
- consumed: Workflow checks and verify gate consume the updated pointer structure.

## Notes / Decisions

- Default choices made: Keep mandatory workflow fields while shrinking pointer files.
- Alternatives considered: Leave CURRENT/LAST verbose; rejected because it conflicts with stated reform goal.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision: No new runtime/user-visible defect; no new issue-memory entry needed.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because` this is a one-off repo-structure alignment task.

## Results

- Files changed:
  - `AGENTS.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260401-md-navigation-pointer-alignment.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260401-md-navigation-pointer-alignment.md`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- Verification summary:
  - `python scripts/workflow_checks.py` -> `0 (ok)`
  - first canonical verify attempt failed at `lite scenario replay` (`S00_lite_headless`, `S16_lite_fixer_loop_pass`)
  - minimal fix: restore `## Acceptance` in CURRENT and update/fix S16 fixture patch syntax+context
  - second canonical verify attempt failed at `patch check` due out-of-scope temp file `simlab_last_debug.json`
  - minimal fix: remove temp debug file and rerun canonical verify
  - final `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0 (OK)` with lite replay `passed=14 failed=0`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
