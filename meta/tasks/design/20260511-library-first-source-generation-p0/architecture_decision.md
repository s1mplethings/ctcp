# Architecture Decision

## Architecture Choice

Add a small helper layer around the existing source_generation path instead of replacing the orchestrator.

## Module Boundaries

- `project_generation_provider_payload.py` owns provider payload parsing and normalization.
- `project_generation_provider_source_files.py` owns materializing normalized provider file rows.
- `project_generation_library_first.py` owns library plan, file manifest, file task generation, and library usage verification.
- `project_generation_source_stage.py` owns stage sequencing and report integration.
- `api_source_chunking.py` owns provider manifest/file-content batch calls.

## Technical Tradeoffs

- Reusing chunked source_generation gives a real provider-file loop immediately, but full per-file retry/escalation remains a later model-budget task.
- Heuristic library plans are sufficient for P0 evidence and verification; future Librarian RAG can replace or enrich selection.
- The verifier checks static imports and declared runtime commands without installing generated-project dependencies.

## Key Constraints

- Production local business templates stay disabled when provider-authored source is absent.
- New checks must be additive and must not weaken generic/domain/smoke validation.
- Generated run outputs remain outside the repo.
