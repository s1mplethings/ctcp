# Task - md-navigation-pointer-alignment

## Active Task

- Queue Item: `ADHOC-20260401-md-navigation-pointer-alignment`
- Layer/Priority: `L2 / P1`
- Archive Task File: [`meta/tasks/archive/20260401-md-navigation-pointer-alignment.md`](archive/20260401-md-navigation-pointer-alignment.md)

## Task Truth Source (pointer)

- task_purpose: Align MD navigation claims with actual repo files and restore thin-pointer task/report flow.
- allowed_behavior_change: `AGENTS.md`; `meta/backlog/execution_queue.json`; `meta/tasks/CURRENT.md`; `meta/tasks/ARCHIVE_INDEX.md`; `meta/tasks/archive/20260401-md-navigation-pointer-alignment.md`; `meta/reports/LAST.md`; `meta/reports/archive/20260401-md-navigation-pointer-alignment.md`; `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`.
- forbidden_goal_shift: No script/runtime/frontend/backend logic edits.
- in_scope_modules: `AGENTS.md`, `meta/`, `tests/fixtures/patches/`.
- out_of_scope_modules: `scripts/`, `frontend/`, `tests/` (except `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`), `src/`, `include/`, `web/`.
- completion_evidence: AGENTS TOC present + CURRENT/LAST thin-pointer format + canonical verify pass.

## Analysis / Find

- Entrypoint analysis: agent startup consumes `CURRENT.md` then follows archive pointer.
- Downstream consumer analysis: `LAST.md` summary and archive report provide execution evidence.
- Source of truth: `AGENTS.md`, active queue item, this task pointer, and archive task/report files.
- Current break point / missing wiring: AGENTS had no TOC marker; CURRENT/LAST drifted from thin-pointer target.
- Repo-local search sufficient: `yes`.

## Integration Check

- upstream: user request + `.agent_private/NOTES.md` reform intent.
- current_module: contract/task/report pointer files.
- downstream: faster agent bootstrap with lower read overhead.
- source_of_truth: queue item + archive task/report entries.
- fallback: keep mandatory fields while compressing pointer files.
- acceptance_test: `python scripts/workflow_checks.py`; `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
- forbidden_bypass: skip queue/task/report binding; remove required workflow evidence fields.
- user_visible_effect: markdown navigation and startup checklist become consistent.

## Plan

1) Bind new ADHOC item and set CURRENT/LAST to pointer-first structure.
2) Add AGENTS TOC anchors.
3) Create archive task/report entries and update indices.
4) Run verify and close with evidence.

## Check / Contrast / Fix Loop Evidence

- check: NOTES reform claims and current files were inconsistent.
- contrast: required state is TOC + thin-pointer flow.
- fix: add TOC and move detailed records into archive with pointer files.

## Completion Criteria Evidence

- completion criteria: `connected + accumulated + consumed`.
- connected/accumulated/consumed evidence is tracked in the archive task/report and verify output.

## Notes / Decisions

- issue memory decision: none (docs/meta alignment only).
- skillized: no, because this is one scoped repository hygiene task, not a reusable runtime workflow.

## Acceptance

- [x] Code changes allowed (Docs-only, no code dirs touched)
