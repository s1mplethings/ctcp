# UX Flow

## Primary User Flow

1. Planner writes `artifacts/file_request.json`.
2. Local Librarian reads the request.
3. Librarian searches mandatory contracts, explicit needs, keyword candidates, token-vector candidates, historical reports, and library docs when present.
4. Librarian writes `context_pack.json` and `librarian_context_pack.json`.
5. Downstream planner/source_generation consumes the context and can inspect retrieval trace when behavior is blocked or low-confidence.

## Key States

- `request_valid`: file_request schema is valid.
- `retrieval_trace_ready`: candidate stages and selected rows are recorded.
- `context_pack_ready`: compatibility context pack exists.
- `librarian_pack_ready`: companion librarian context pack exists.
- `librarian_failed`: structured failure artifact exists.

## Success Path

Sparse project-generation requests include relevant CTCP contracts, report/failure memory, and library docs with provenance and constraints.

## Failure Path

Invalid requests or missing mandatory authority files produce `context_pack.failure.json` and do not fake success.
