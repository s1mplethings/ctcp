# Task Archive - Library-first source_generation P0 foundation

## Queue Binding

- Queue Item: `ADHOC-20260511-library-first-source-generation-p0`
- Lane: `Virtual Team Lane`
- Status: `done`

## Scope

First landing slice for the user-provided CTCP next-stage plan:
- provider source payload normalization
- library-first source_generation artifacts
- file manifest and file task contracts
- library usage verification
- single-file default chunked source_generation batches

Deferred:
- full Librarian vector/RAG implementation
- full model budget controller
- success/failure experience ingestion

## Changes

- Added schema contracts:
  - `contracts/project_library_plan.schema.json`
  - `contracts/file_manifest.schema.json`
  - `contracts/file_task.schema.json`
  - `contracts/library_usage_verification.schema.json`
- Added:
  - `tools/providers/project_generation_provider_payload.py`
  - `tools/providers/project_generation_library_first.py`
  - `tests/test_project_generation_library_first.py`
- Updated:
  - `tools/providers/project_generation_provider_source_files.py`
  - `tools/providers/project_generation_source_stage.py`
  - `llm_core/providers/api_source_chunking.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_source_chunking.py`

## Results

- Source_generation now writes and reports:
  - `artifacts/library_plan.json`
  - `artifacts/file_manifest.json`
  - `artifacts/file_tasks/*.json`
  - `artifacts/library_usage_verification.json`
- Library usage verification is consumed by `_blocked_by_validation()`.
- Chunked source_generation defaults to one file per content batch.
- Existing provider-authored source provenance behavior remains intact.

## Verify

- PASS: py_compile for changed Python modules returned 0.
- PASS: focused library-first tests returned 0, 4 tests OK.
- PASS: API source chunking tests returned 0, 2 tests OK.
- PASS: provider provenance tests returned 0, 4 tests OK.
- PASS: project generation artifact tests returned 0, 48 tests OK.
- PASS: API agent template tests returned 0, 22 tests OK.
- PASS: workflow/module/patch/code-health focused gates returned 0.
- PASS: canonical `verify_repo.ps1 -Profile code` with `CTCP_SKIP_LITE_REPLAY=1` returned 0.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: source_generation writes library-first artifacts from the existing provider source path.
- accumulated: run artifacts preserve provider rows, library plan, file manifest, file tasks, and verification output.
- consumed: source_generation pass/block logic consumes `library_usage_verification.passed`.

## Issue Memory Decision Evidence

- No new issue-memory entry.
- Reason: the task addresses an existing source_generation failure class; no new distinct recurring failure was introduced.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- skillized: no, because this is runtime infrastructure rather than a reusable agent workflow.
- persona_lab_impact: none.
