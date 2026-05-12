# Product Direction

## Direction

Make local knowledge retrieval visible and reusable without requiring external embedding services in the first P2 slice.

## MVP Scope

- Add deterministic hybrid retrieval: keyword search plus token-vector style scoring.
- Add retrieval trace and selected_context rows.
- Add downstream constraints that keep Librarian as evidence provider, not code generator.
- Write `artifacts/librarian_context_pack.json` alongside `artifacts/context_pack.json`.

## Non-Goals

- Persistent SQLite vector store.
- Ollama embedding runtime dependency.
- Model tier routing.
- Generated project source writing.

## Priority Choices

1. Compatibility with existing local librarian runtime.
2. Auditable retrieval evidence.
3. Sparse request improvement for source_generation/library-first tasks.
4. Future-ready schema surface for later Ollama/vector persistence.
