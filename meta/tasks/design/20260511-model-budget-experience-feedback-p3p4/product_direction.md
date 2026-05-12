# Product Direction - Model budget and experience feedback P3/P4

## Product Direction

Make CTCP's next-generation project generation loop auditable and reusable without requiring a new external service.

## MVP Scope

- Deterministic model budget policy with tier names, stage choices, limits, and escalation evidence.
- Source_generation budget artifact and report references.
- Chunked source_generation phase evidence for manifest and file-author batches.
- Librarian experience records and recipe candidates written from source_generation reports.
- Retrieval support for local experience records when present.

## Non-Goals

- No provider-specific model ID switching.
- No Ollama embedding persistence.
- No SQLite vector store.
- No generated project source repair in this patch.

## Priority Choices

Favor stable local evidence and tests over a broad routing rewrite.
