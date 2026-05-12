# Implementation Plan

## Build Order

1. Add schema files for the new artifacts.
2. Add provider payload normalization helper and route provider row extraction through it.
3. Add library-first helper to build and write `library_plan`, `file_manifest`, `file_tasks`, and `library_usage_verification`.
4. Connect helper output into `normalize_source_generation_stage()` and source report.
5. Change chunked source_generation default batch size to one file.
6. Update prompt wording to describe manifest plus single-file content batches.
7. Add focused tests and run acceptance gates.

## Handoff Sequence

- Product/spec evidence is represented by run artifacts.
- Build lead owns helper modules and stage integration.
- QA owns tests around payload shapes, artifact output, batch default, and verifier failures.

## Implementation Stop Conditions

- Any change would require provider credentials.
- Any change would require weakening current production source gates.
- Any change would touch generated external project source manually.
