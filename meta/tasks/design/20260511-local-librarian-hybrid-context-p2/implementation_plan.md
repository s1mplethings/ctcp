# Implementation Plan

## Build Order

1. Add schema contracts.
2. Add `tools/librarian_retrieval.py`.
3. Extend `build_context_pack()` with retrieval trace, selected_context, missing_context, and downstream constraints.
4. Update `ctcp_librarian.py` to write `librarian_context_pack.json`.
5. Add focused tests.
6. Run focused and canonical gates.

## Handoff Sequence

- Librarian produces evidence only.
- Planner/source_generation consume context.
- Verification confirms artifact shape and no regression to legacy context pack.

## Implementation Stop Conditions

- Any change requires live Ollama.
- Any change requires replacing the existing context pack schema.
- Any change writes generated project source.
