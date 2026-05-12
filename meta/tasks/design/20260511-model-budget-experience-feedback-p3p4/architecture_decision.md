# Architecture Decision - Model budget and experience feedback P3/P4

## Architecture Choice

Add small deterministic helper modules:

- `tools/providers/project_generation_model_budget.py`
- `tools/librarian_experience.py`

Then integrate them at existing source_generation and chunked API boundaries.

## Module Boundaries

- Model budget module owns tier policy and escalation record shape.
- Source stage owns artifact writing and report attachment.
- Chunked source generation owns phase-level budget evidence for manifest and file batches.
- Librarian experience module owns source_generation outcome summarization and recipe candidate materialization.
- Retrieval module only reads evidence; it does not generate project source.

## Tradeoffs

This patch records tier decisions but does not change provider credentials or selected model IDs. That keeps behavior deterministic and testable while leaving provider-specific routing for a later integration.

## Key Constraints

- No network dependency.
- Preserve existing artifacts and report fields.
- Keep Librarian evidence-only.
