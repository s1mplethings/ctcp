# Decision Log

## Accepted Assumptions

- The first landing slice should use existing chunked source_generation instead of building a new provider dispatch graph.
- Full Librarian RAG and model budget routing are separate tasks because they require new storage/provider contracts and broader runtime wiring.
- Library-first verification should be additive and block delivery only for declared library constraints in this patch.

## Unresolved Decisions

- Exact long-term model tier names and provider routing policy.
- Whether generated projects may declare and install third-party dependencies during validation.
- Which library documentation sources become the first Librarian ingestion corpus.

## Rationale

This scope creates immediate runtime evidence and delivery protection around source_generation without pretending the full roadmap is complete.
