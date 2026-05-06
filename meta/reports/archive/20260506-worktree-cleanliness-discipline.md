# Demo Report - Worktree Cleanliness Discipline

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
- Added daily worktree cleanliness rules to `docs/cleanup_policy.md`.
- Added `scripts/worktree_cleanliness_report.py`.
- Added `tests/test_worktree_cleanliness_report.py`.
- Updated task, report, queue, and archive metadata.

### Verify
- `.venv\Scripts\python.exe -m py_compile scripts\worktree_cleanliness_report.py tests\test_worktree_cleanliness_report.py` -> exit 0.
- `.venv\Scripts\python.exe -m unittest tests.test_worktree_cleanliness_report -v` -> exit 0, 4 tests OK.
- `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json` -> exit 0.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0.
- lane regressions -> exit 0.
- `.venv\Scripts\python.exe scripts\sync_doc_links.py --check` -> exit 0.
- `git diff --check -- <task files>` -> exit 0, CRLF warnings only.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.
- first failure point evidence: none in final canonical verify.
- minimal fix strategy evidence: use advisory classification and task grouping; do not destructively reset.
- triplet runtime wiring command evidence: canonical verify ran `test_runtime_wiring_contract.py` and passed.
- triplet issue memory command evidence: canonical verify ran `test_issue_memory_accumulation_contract.py` and passed.
- triplet skill consumption command evidence: canonical verify ran `test_skill_consumption_contract.py` and passed.

### Questions
- None.

### Demo
- `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py`
- Current dirty summary after report/archive closeout:
  - total: `162`
  - source/test: `68`
  - docs/contract/workflow: `22`
  - task/report archive: `68`
  - task/report meta: `4`
  - runtime/generated output: `0`

### Dirty State
- Post-commit closeout:
  - `git status --short --untracked-files=all` returned no rows.
  - `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json` returned `total_dirty: 0`.
- No inherited work was reverted or deleted; the user approved grouping it into commits.

### Integration Proof
- connected: advisory command reads git dirty state.
- accumulated: bucket counts are recorded in report/task archive.
- consumed: cleanup policy now defines the future closeout flow.

### Skill Decision
- skillized: no, because this is a repo-local hygiene helper; existing `ctcp-workflow` remains the reusable workflow.
