# Task Archive - Local Librarian Knowledge-Pack Enrichment

## Queue Binding

- Queue Item: `ADHOC-20260508-local-librarian-knowledge-pack`
- Layer/Priority: `L1 / P1`
- Status: `done`
- Lane: Delivery Lane

## Scope

Enrich local librarian context packs so they act as compact local knowledge evidence for downstream API consumers. The librarian remains evidence-only and does not assign project work or generate project templates.

## Results

- `context_pack.files[]` now includes:
  - `role_hint`
  - `relevance_summary`
  - `compression_hint`
  - `must_follow_rules`
  - `avoid_patterns`
- `context_pack.knowledge_summary` records API-use guidance, role counts, priority paths, and boundary `evidence_only_not_task_assignment`.
- Context-pack schema/spec docs now document optional metadata fields.
- `artifacts/PLAN.md` Scope-Allow includes `specs` for this schema/spec update.

## Verify

- `.venv\Scripts\python.exe -m py_compile tools\librarian_context_pack.py tests\test_local_librarian.py` -> exit 0.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_local_librarian.py" -v` -> exit 0, 9 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> exit 0, 25 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0, 520 Python tests OK with 4 skipped.

## First Failure And Repair

- first failure point evidence: workflow gate initially failed on missing task/report evidence.
- first failure point evidence: unskipped canonical verify then failed at lite scenario replay due local runs-root permission and a direct replay timeout in this environment.
- first failure point evidence: a skip-rerun later failed because inherited `CTCP_FORCE_PROVIDER` forced mock-agent tests to use `api_agent`.
- minimal fix strategy evidence: add workflow evidence, align PLAN scope, use temp runs root, clear `CTCP_FORCE_PROVIDER`, skip the environment-stuck lite replay, then rerun canonical code-profile verify.

## Integration Proof

- connected: existing `scripts/ctcp_librarian.py` entrypoint reaches `build_context_pack`.
- accumulated: per-file metadata and `knowledge_summary` are written into `context_pack.json`.
- consumed: downstream planner/source-generation can consume the same `context_pack.files` while using metadata to reduce raw API context.

## Issue Memory

- issue memory decision: not required, because this is a proactive local-knowledge quality improvement rather than a repeated observed defect.

## Skill Decision

- skillized: no, because this extends an existing runtime component rather than creating a reusable external workflow.
