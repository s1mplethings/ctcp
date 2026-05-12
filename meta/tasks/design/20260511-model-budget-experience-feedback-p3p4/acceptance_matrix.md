# Acceptance Matrix - Model budget and experience feedback P3/P4

## Acceptance Criteria

| Criterion | Check |
|---|---|
| Model budget policy exists | focused model budget tests |
| Source_generation writes budget artifact | library-first source_generation regression |
| Chunked source_generation records budget phase evidence | API chunking regression |
| Experience feedback records pass/blocked outcome | experience feedback tests |
| Retrieval can select experience records | librarian retrieval test |
| Repo workflow remains valid | workflow/module/patch/code-health/canonical verify |

## Smoke Checks

- `artifacts/model_budget.json` has `ctcp-model-budget-v1`.
- `artifacts/librarian_experience_record.json` has `ctcp-librarian-experience-record-v1`.
- Source report includes paths to both artifact families.

## Failure Interpretation

The first failing focused test identifies the local repair target. Canonical verify is run after focused tests pass.
