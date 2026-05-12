# Decision Log - Model budget and experience feedback P3/P4

## Accepted Decisions

- Use deterministic tier policy now; defer provider-specific model switching.
- Write experience records as evidence artifacts; do not auto-ingest into a persistent vector store.
- Extend local retrieval to include experience-record style files when they exist.

## Unresolved Decisions

- Exact provider model IDs per tier are deferred to a later provider-routing task.
- Persistent Ollama embedding refresh cadence is deferred to a later Librarian persistence task.

## Rationale

This completes the new runtime surface without adding external moving parts or making source_generation less stable.
