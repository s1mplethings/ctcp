# Product Direction

## Direction

Make source_generation evidence-driven and library-first while preserving the current production rule that generated business source must be provider-authored.

## MVP Scope

- Add `library_plan`, `file_manifest`, `file_task`, and `library_usage_verification` artifacts.
- Normalize provider source payloads from common JSON shapes into `path` / `content` rows.
- Use the existing chunked source_generation path as the near-term provider-file loop, with one-file batches by default.
- Verify required imports, forbidden patterns, syntax, runtime commands when declared, and placeholder markers.

## Non-Goals

- Full local vector RAG implementation.
- Full model-tier budget controller and escalation routing.
- A new external run or hand-authored generated project.
- Replacing the whole source_generation orchestrator in one patch.

## Priority Choices

1. Production safety and delivery blocking.
2. File-level provenance and verification artifacts.
3. Payload normalization compatibility.
4. Prompt alignment and batch-size default.
5. Later RAG/model-budget work as separate queue items.
