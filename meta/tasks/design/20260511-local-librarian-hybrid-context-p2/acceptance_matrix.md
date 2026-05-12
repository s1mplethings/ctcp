# Acceptance Matrix

| Criterion | Check |
| --- | --- |
| Retrieval trace has keyword and token-vector stages | `tests.test_librarian_hybrid_context` |
| Companion librarian context pack is written | `tests.test_librarian_hybrid_context` |
| Sparse request retrieves docs/reports/library docs when present | `tests.test_librarian_hybrid_context` |
| Existing context pack behavior remains compatible | `tests.test_local_librarian` |
| Repo task evidence is complete | `scripts/workflow_checks.py` |

## Smoke Checks

- `context_pack.json` remains `ctcp-context-pack-v1`.
- `librarian_context_pack.json` uses `ctcp-librarian-context-pack-v1`.
- Retrieval trace contains candidate stages and selected paths.

## Success / Failure Evaluation

- Success: focused librarian tests and canonical verify pass.
- Failure: first failing test/gate and minimal repair are recorded in report.
