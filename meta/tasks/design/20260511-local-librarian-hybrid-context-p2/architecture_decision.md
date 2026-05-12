# Architecture Decision

## Architecture Choice

Extend the existing Librarian entrypoint with a dependency-free retrieval helper instead of creating a disconnected `tools/librarian/` subsystem.

## Module Boundaries

- `tools/librarian_retrieval.py` owns hybrid candidate collection, token scoring, and retrieval trace formatting.
- `tools/librarian_context_pack.py` owns context-pack construction and compatibility fields.
- `scripts/ctcp_librarian.py` owns CLI artifact writes.
- Schema files under `contracts/` define the new evidence shape.

## Technical Tradeoffs

- Deterministic token-vector scoring is not a semantic embedding replacement, but it gives a local, testable vector-like lane and trace now.
- Writing a companion artifact avoids breaking existing consumers of `context_pack.json`.
- Full Ollama embedding can later replace or augment the vector-like lane behind the same trace contract.

## Key Constraints

- No network or service dependency.
- No generated project source authoring.
- No replacement of current context_pack output.
