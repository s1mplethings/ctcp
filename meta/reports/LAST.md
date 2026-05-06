# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260506-worktree-cleanliness-discipline.md`
- Date: `2026-05-06`
- Topic: `Worktree Cleanliness Discipline`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/cleanup_policy.md`
- `scripts/verify_repo.ps1`
- `tools/module_protection.py`
- `scripts/workflow_checks.py`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`

### Plan
1. Bind `ADHOC-20260506-worktree-cleanliness-discipline`.
2. Extend cleanup policy with daily non-destructive worktree discipline.
3. Add a read-only advisory dirty-state report command.
4. Add focused tests for status parsing and classification.
5. Run focused tests, workflow/module checks, lane regressions, and canonical verify.
6. Record the current dirty state and next cleanup order.

### Changes
- `docs/cleanup_policy.md`
  - Added daily worktree cleanliness rules.
  - Added closeout requirements for `git status --short`, runtime-output handling, grouping source/docs by task, and avoiding destructive resets.
- `scripts/worktree_cleanliness_report.py`
  - Added a read-only advisory command that consumes `git status --short --untracked-files=all`.
  - Classifies files into source/test, docs/contract/workflow, task/report archive, task/report meta, runtime/generated output, and other buckets.
  - Supports text and JSON output plus optional runtime-output failure mode.
- `tests/test_worktree_cleanliness_report.py`
  - Covered status parsing, rename parsing, category classification, and report counts.
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/ARCHIVE_INDEX.md`
- `meta/tasks/archive/20260506-worktree-cleanliness-discipline.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260506-worktree-cleanliness-discipline.md`
  - Bound and closed the task with verify evidence.

### Verify
- Passed:
  - `.venv\Scripts\python.exe -m py_compile scripts\worktree_cleanliness_report.py tests\test_worktree_cleanliness_report.py` -> exit 0.
  - `.venv\Scripts\python.exe -m unittest tests.test_worktree_cleanliness_report -v` -> exit 0, 4 tests OK.
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json` -> exit 0.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v` -> exit 0.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_support_to_production_path.py" -v` -> exit 0.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_backend_interface_contract_apis.py" -v` -> exit 0.
  - `.venv\Scripts\python.exe scripts\sync_doc_links.py --check` -> exit 0.
  - `git diff --check -- docs\cleanup_policy.md scripts\worktree_cleanliness_report.py tests\test_worktree_cleanliness_report.py meta\backlog\execution_queue.json meta\tasks\CURRENT.md` -> exit 0, CRLF warnings only.
  - `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.
- Canonical verify summary:
  - profile: `code`
  - ownership: `lane-owned`
  - lite replay: `15 passed / 0 failed`
  - python unit tests: `517 tests OK, 4 skipped`
  - result: `OK`
- first failure point evidence:
  - none in the final canonical verify run.
  - current risk remains a dirty worktree, not a failing gate.
- minimal fix strategy evidence:
  - keep the advisory report read-only, document the closeout rules, and clean future state by commit/stash grouping rather than destructive reset.
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was executed by canonical verify and passed.
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was executed by canonical verify and passed.
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was executed by canonical verify and passed.

### Questions
- None.

### Demo
- New command:
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py`
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json`
- Current advisory inventory after report/archive closeout:
  - total dirty files: `162`
  - `source_or_test_change`: `68`
  - `docs_contract_or_workflow_change`: `22`
  - `task_report_archive`: `68`
  - `task_report_meta`: `4`
  - `runtime_or_generated_output`: `0`
- Practical cleanup order:
  - no runtime/generated output needs deletion first.
  - next, group untracked source/test files by completed queue item and commit or stash them.
  - then group docs/meta/report archives by task and commit or stash them.

### Dirty State
- Post-commit closeout:
  - `git status --short --untracked-files=all` returned no rows.
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json` returned `total_dirty: 0`.
- This task did not revert or delete inherited dirty files; the user approved grouping them into commits.
- The current worktree is clean after the grouped commits.

### Integration Proof
- connected: `scripts/worktree_cleanliness_report.py` consumes `git status --short --untracked-files=all`.
- accumulated: dirty count and bucket summary are recorded in this report and the task archive.
- consumed: `docs/cleanup_policy.md` now points future task closeout to the advisory command and cleanup order.

### Skill Decision
- skillized: no, because this is a repo-local hygiene helper; existing `ctcp-workflow` remains the reusable workflow.
