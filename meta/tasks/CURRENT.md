# Task - Worktree Cleanliness Discipline

## Queue Binding

- Queue Item: `ADHOC-20260506-worktree-cleanliness-discipline`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user asked to solve remaining issues one by one and keep the project clean going forward.
- Dependency check: `ADHOC-20260505-dirty-worktree-verification-closure = done`
- Lane: Delivery Lane.
- Scope boundary: add non-destructive worktree cleanliness discipline and an advisory dirty-state inventory; do not revert, delete, commit, or hide existing dirty files.

## Task Truth Source

- task_purpose:
  - Make the current dirty-worktree state visible and repeatable.
  - Document how to keep the repo clean after each task.
  - Provide a small advisory command that classifies dirty files before cleanup or commit decisions.
- allowed_behavior_change:
  - `docs/cleanup_policy.md`
  - `scripts/worktree_cleanliness_report.py`
  - `tests/test_worktree_cleanliness_report.py`
  - task/report/queue metadata for this topic.
- forbidden_goal_shift:
  - Do not discard or revert existing dirty files.
  - Do not turn the advisory cleanliness report into a blocking verify gate in this patch.
  - Do not combine this with generated-project quality or support bot behavior changes.
- in_scope_modules:
  - cleanup policy
  - advisory worktree report command
  - focused unit tests for classification logic
  - current task/report/archive metadata
- out_of_scope_modules:
  - provider code quality repairs
  - Telegram bot runtime behavior
  - generated-project live retests
  - committing, stashing, or deleting existing dirty source/report files
- completion_evidence:
  - The advisory report command runs and reports the current dirty state.
  - The cleanup policy states daily cleanliness rules and non-destructive cleanup order.
  - Focused tests and repo workflow/module-protection checks are recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `docs/cleanup_policy.md`
  - `scripts/worktree_cleanliness_report.py`
  - `tests/test_worktree_cleanliness_report.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260506-worktree-cleanliness-discipline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260506-worktree-cleanliness-discipline.md`
  - `docs/03_quality_gates.md`
  - `frontend/support_reply_policy.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_runtime_wiring_contract.py`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - Do not use `git reset --hard`, `git checkout --`, or destructive cleanup commands.
  - Do not weaken module-protection, patch, or verify gates to mask dirty files.
  - Do not claim the worktree is clean unless `git status --short` is empty.
- Acceptance Checks:
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json`
  - `.venv\Scripts\python.exe -m unittest tests.test_worktree_cleanliness_report -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Entrypoint analysis: the user needs a repeatable way to see dirty state before choosing commit/stash/cleanup.
- Downstream consumer analysis: future CTCP tasks and reports consume the cleanliness policy and advisory inventory.
- Source of truth: `git status --short --untracked-files=all`, `docs/cleanup_policy.md`, and `meta/reports/LAST.md`.
- Current break point / missing wiring: anti-pollution catches build/run outputs, but there is no small daily command that classifies all dirty files into action buckets.
- Repo-local search sufficient: yes.
- If no, external research artifact: none.

## Integration Check

- upstream: existing dirty worktree from project-generation, support-bot splitting, API, librarian, and report tasks.
- current_module: cleanup policy plus advisory worktree report command.
- downstream: future task closeout uses the advisory report before commit/stash/delete decisions.
- source_of_truth: `git status --short --untracked-files=all`.
- fallback: if advisory report fails, use raw `git status --short --untracked-files=all` and record first failure.
- acceptance_test:
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json`
  - `.venv\Scripts\python.exe -m unittest tests.test_worktree_cleanliness_report -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
- forbidden_bypass:
  - no destructive reset/revert
  - no cleanup gate weakening
  - no claim of clean worktree while dirty files remain
- user_visible_effect: user can see exactly what remains dirty and the order to clean it without losing work.

## DoD Mapping

- [x] DoD-1: Repository cleanup policy explains daily worktree cleanliness discipline without authorizing destructive resets.
- [x] DoD-2: An advisory command classifies dirty worktree state into source, docs/meta, archive, and runtime-output buckets.
- [x] DoD-3: Current dirty state and the first next cleanup actions are recorded without reverting user or previous task changes.

## Check/Contrast/Fix Loop Evidence

- check:
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json` returned dirty total 162 after report/archive closeout.
  - `.venv\Scripts\python.exe -m unittest tests.test_worktree_cleanliness_report -v` passed 4 tests.
  - canonical verify passed under code profile.
- contrast:
  - expected output should classify current dirty files without modifying them.
  - actual output classified dirty files into docs/contract/workflow, source/test, task/report archive, and task/report meta buckets.
- fix:
  - implemented a read-only advisory reporter.
  - documented the cleanup order and non-destructive daily rules.

## Issue Memory Decision Evidence

- issue_memory_decision: no new issue-memory entry yet; this is a worktree hygiene tool and policy. Add one only if a repeated dirty-state failure blocks delivery again.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: the advisory command connects to git status.
- accumulated: the current dirty count and bucket summary are recorded in `meta/reports/LAST.md`.
- consumed: the cleanup policy points future tasks to the advisory command and closeout order.

## Plan

1. Add the queue item and bind this task.
2. Extend cleanup policy with daily worktree cleanliness rules.
3. Add a read-only advisory worktree report command.
4. Add focused tests for status parsing and bucket classification.
5. Run focused tests and workflow/module-protection checks.
6. Record dirty-state evidence and next cleanup order.
7. Run canonical verify or record the first failure and minimal fix.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed.
- [x] Advisory report runs.
- [x] Focused unit tests pass.
- [x] Workflow and module-protection checks pass.
- [x] Canonical verify pass or first failure recorded.
- [x] Demo report updated: `meta/reports/LAST.md`.

## Notes / Decisions

- Default choices made: keep the new command advisory first so current dirty work can be classified before deciding commits/stashes.
- Alternatives considered: hard-failing verify on any dirty worktree was rejected for this patch because the repo intentionally has existing uncommitted work that must not be discarded.
- Any contract exception reference: none.
- Issue memory decision: no new issue-memory entry for this policy/tooling patch.
- Skill decision: skillized: no, because this is a repo-local hygiene helper; existing `ctcp-workflow` remains the reusable workflow.
- persona_lab_impact: none.

## Results

- Files changed:
  - `docs/cleanup_policy.md`
  - `scripts/worktree_cleanliness_report.py`
  - `tests/test_worktree_cleanliness_report.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260506-worktree-cleanliness-discipline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260506-worktree-cleanliness-discipline.md`
- Verification summary:
  - focused unit tests passed.
  - lane regressions passed.
  - canonical verify passed with profile `code`, ownership `lane-owned`, lite replay 15 passed / 0 failed, Python tests 517 OK / 4 skipped.
- Queue status update suggestion: `done`.
