# Decision Log

## Accepted Assumptions

- P2 can start with deterministic token-vector scoring while keeping the contract open for later Ollama embeddings.
- `context_pack.json` remains the compatibility artifact.
- `librarian_context_pack.json` is a richer companion artifact for downstream project-generation consumers.

## Unresolved Decisions

- Exact persistent vector store format.
- Ollama model name and availability contract.
- Long-term ingestion cadence for external library docs.

## Rationale

This produces immediate retrieval evidence and downstream constraints without adding an unreliable external dependency to the canonical verify path.
