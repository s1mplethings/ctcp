# Task Archive - Model budget and Librarian experience feedback P3/P4

## Queue Binding

- Queue Item: `ADHOC-20260511-model-budget-experience-feedback-p3p4`
- Lane: `Virtual Team Lane`
- Status: `done`

## Scope

Completed the remaining local runtime pieces from the staged redesign:
- model budget controller
- source_generation model budget evidence
- chunked API model budget phase evidence
- Librarian source_generation experience feedback
- retrieval coverage for local experience records

Deferred:
- provider-specific model ID routing
- persistent Ollama embeddings
- SQLite vector store

## Changes

- Added:
  - `contracts/model_budget.schema.json`
  - `contracts/librarian_experience_record.schema.json`
  - `tools/providers/project_generation_model_budget.py`
  - `tools/librarian_experience.py`
  - `tests/test_project_generation_model_budget.py`
  - `tests/test_librarian_experience_feedback.py`
- Updated:
  - `tools/providers/project_generation_source_stage.py`
  - `llm_core/providers/api_source_chunking.py`
  - `tools/librarian_retrieval.py`
  - affected focused regressions

## Results

- `artifacts/model_budget.json` is written by source_generation.
- `artifacts/librarian_experience_record.json` and `artifacts/librarian_recipe_candidate.json` are written by source_generation.
- Chunked source_generation records model budget choices for manifest and file batches.
- Retrieval can select local experience records.

## Verify

- PASS: focused new tests returned 0, 6 tests OK.
- PASS: affected regressions returned 0, 9 tests OK.
- PASS: workflow/module/patch/code-health focused gates returned 0.
- PASS: canonical `verify_repo.ps1 -Profile code` with `CTCP_SKIP_LITE_REPLAY=1` returned 0.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: source_generation and chunked source_generation call the new helper modules.
- accumulated: model budget and experience feedback artifacts persist run learning.
- consumed: source_generation reports reference the artifacts and retrieval can select experience records.

## Issue Memory Decision Evidence

- No new issue-memory entry.
- Reason: no recurring production failure was found; this was a feature completion task.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- skillized: no, because this is runtime functionality rather than a reusable agent workflow.
- persona_lab_impact: none.
