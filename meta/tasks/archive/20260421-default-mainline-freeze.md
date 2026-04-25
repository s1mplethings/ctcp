# Task - default-mainline-freeze

## Queue Binding

- Queue Item: `ADHOC-20260421-default-mainline-freeze`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the default mainline has been wired through `run_manifest`; the next step is to verify it strictly and freeze the protected mainline surface.
- Dependency check:
  - `ADHOC-20260421-unified-mainline-run-manifest = done`
- Scope boundary: first perform read-only validation of the existing mainline; only if it passes, add freeze contract, hash manifest, and freeze test. Do not rewrite routing, ADLC, librarian, whiteboard, bridge, or run_manifest runtime logic.

## Task Truth Source (single source for current task)

- task_purpose:
  - verify that the default mainline is implemented as one same-run chain
  - freeze the verified mainline surface with a contract, hash manifest, and regression test
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/`
  - `meta/reports/`
  - `meta/tasks/`
  - `docs/architecture/contracts/default_mainline_freeze_contract.md`
  - `artifacts/mainline_freeze_manifest.json`
  - `tests/integration/test_mainline_freeze_manifest.py`
- forbidden_goal_shift:
  - do not alter mainline runtime implementation during verification
  - do not expand or redesign the mainline
  - do not freeze before read-only validation passes
- in_scope_modules:
  - freeze contract
  - freeze manifest
  - freeze manifest test
  - verification/report metadata
- out_of_scope_modules:
  - `docs/02_workflow.md`
  - `docs/architecture/contracts/run_manifest_contract.md`
  - `docs/architecture/contracts/support_whiteboard_contract.md`
  - `docs/architecture/contracts/frontend_bridge_contract.md`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_librarian.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/workflows/adlc_self_improve_core.py`
  - `tools/adlc_gate.py`
  - `tools/run_manifest.py`
  - `tests/integration/test_mainline_run_contract.py`
- completion_evidence:
  - read-only validation log proves the mainline exists and is tested
  - `docs/architecture/contracts/default_mainline_freeze_contract.md` exists
  - `artifacts/mainline_freeze_manifest.json` contains sha256 records for protected files
  - `tests/integration/test_mainline_freeze_manifest.py` passes

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/`
  - `meta/reports/`
  - `meta/tasks/`
  - `docs/architecture/contracts/default_mainline_freeze_contract.md`
  - `artifacts/mainline_freeze_manifest.json`
  - `tests/integration/test_mainline_freeze_manifest.py`
- Protected Paths:
  - all existing default mainline implementation and contract files being verified/frozen
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `N/A - freeze task only adds protection files and does not modify frozen mainline implementation`
- Forbidden Bypass:
  - do not create the freeze manifest until validation passes
  - do not change protected mainline files as part of freezing
  - do not mark completion without running the freeze test
- Acceptance Checks:
  - read-only contract/string checks for the default mainline
  - `python -m unittest discover -s tests/integration -p "test_mainline_run_contract.py" -v`
  - `python -m unittest discover -s tests/integration -p "test_mainline_freeze_manifest.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## Analysis / Find (before plan)

- Entrypoint analysis: bounded Delivery Lane verification/freeze task; no Virtual Team Lane needed.
- Source of truth:
  - `AGENTS.md`
  - `docs/00_CORE.md`
  - `docs/02_workflow.md`
  - `docs/architecture/contracts/run_manifest_contract.md`
  - `tests/integration/test_mainline_run_contract.py`
- Current break point / missing wiring:
  - unknown until read-only validation completes
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: current default runtime mainline docs and runtime scripts.
- current_module: freeze contract/manifest/test.
- downstream: future patches touching protected mainline files fail freeze test unless explicitly unfrozen.
- source_of_truth: new freeze contract plus generated sha256 manifest.
- fallback: if validation fails, do not freeze; report missing items only.
- acceptance_test:
  - `python -m unittest discover -s tests/integration -p "test_mainline_run_contract.py" -v`
  - `python -m unittest discover -s tests/integration -p "test_mainline_freeze_manifest.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - no docs-only freeze without hash manifest
  - no hash manifest without freeze test
- user_visible_effect:
  - the default mainline becomes protected by explicit contract and test.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Read-only validation proves docs, runtime wiring, run_manifest contract, and same-run integration test satisfy the default mainline requirements before any freeze files are added
- [x] DoD-2: A default mainline freeze contract documents the frozen mainline, protected file surface, explicit unfreeze requirement, and future-change explanation rule
- [x] DoD-3: A hash-based freeze manifest plus integration test protect the default mainline files and fail with the changed file path when any protected file drifts

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A - repo-local search sufficient`
- [x] Code changes allowed
- [x] Patch applies cleanly via repo-local file edits in allowed write scope
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. Run read-only validation against docs, runtime write points, contract fields, and existing E2E test.
2. If any validation fails, stop without freezing and report gaps.
3. If validation passes, add `default_mainline_freeze_contract.md`.
4. Generate `artifacts/mainline_freeze_manifest.json` with sha256 for protected files.
5. Add `tests/integration/test_mainline_freeze_manifest.py`.
6. Run focused mainline and freeze tests.
7. Run workflow checks and canonical verify or isolated verify if the shared dirty worktree blocks module protection.
8. Record all logs and close the task.

## Notes / Decisions

- Check/Contrast/Fix evidence: run read-only checks first, then freeze only after the focused mainline E2E passes; if any gate fails, apply the smallest scoped fix and rerun the same gate.
- Completion criteria evidence: complete only when the frozen mainline remains connected + accumulated + consumed through docs/contracts, runtime write points, run_manifest, and tests.
- Issue memory decision: no issue memory entry needed; this is a planned freeze after successful validation, not a recurring user-visible failure.
- Skill decision (`skillized: no, because ...`): `skillized: no, because this is a repository freeze contract and regression gate, not a reusable agent workflow; existing ctcp-workflow/ctcp-verify skills cover execution and verification.`
- persona_lab_impact: none

## Results

- Files changed:
  - `docs/architecture/contracts/default_mainline_freeze_contract.md`
  - `artifacts/mainline_freeze_manifest.json`
  - `tests/integration/test_mainline_freeze_manifest.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260421-unified-mainline-run-manifest.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260421-unified-mainline-run-manifest.md`
- Verification summary:
  - read-only docs/contract/runtime/test string checks => pass
  - `python -m unittest discover -s tests/integration -p "test_mainline_run_contract.py" -v` => `0`
  - `python -m unittest discover -s tests/integration -p "test_mainline_freeze_manifest.py" -v` => `0`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0`
  - `python scripts/workflow_checks.py` => `0`
  - main workspace `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`, first failure `module protection check` due unrelated dirty files outside this task's allowed scope
  - isolated workspace `D:\.c_projects\cqa`, clean snapshot commit `50b1dca`, `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
