# Implementation Plan - Model budget and experience feedback P3/P4

## Build Order

1. Add contracts for model budget and Librarian experience record.
2. Implement deterministic model budget helper.
3. Implement Librarian experience helper.
4. Integrate source_generation artifact writes and report references.
5. Integrate chunked source_generation phase budget evidence.
6. Extend retrieval search roots for local experience records.
7. Add focused tests.
8. Run focused tests, scoped gates, and canonical verify.

## Stop Conditions

- Stop if integration requires provider credentials or external services.
- Stop if a change would manually modify generated project source.
- Stop if source_generation report compatibility breaks.
