# Acceptance Matrix

## Criteria

| Criterion | Check |
| --- | --- |
| Provider payloads normalize to source rows | `tests.test_project_generation_library_first` |
| Source_generation writes library/file artifacts | `tests.test_project_generation_library_first` |
| Library usage violations block report | `tests.test_project_generation_library_first` |
| Chunked provider content defaults to one file per batch | `tests.test_api_source_chunking` |
| Existing provider provenance behavior remains intact | `tests.test_project_generation_provenance` |
| Workflow/meta gates accept task binding | `scripts/workflow_checks.py` |

## Smoke Checks

- Provider row extraction accepts `files`, `provider_source_files`, `source_bundle.files`, `content`, and `content_lines`.
- Library usage verifier detects missing required imports and forbidden manual parsing/table rendering patterns.
- Source_generation report records `library_plan_path`, `file_manifest_path`, `file_task_paths`, and `library_usage_verification_path`.

## Success / Failure Evaluation

- Success: focused tests pass and canonical verify profile is recorded.
- Failure: first failing test or verify gate is recorded in `meta/reports/LAST.md` with a minimal repair strategy.
