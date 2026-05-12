# UX Flow - Model budget and experience feedback P3/P4

## Primary Operator Flow

1. A project generation run reaches source_generation.
2. Source_generation writes existing library-first artifacts.
3. Source_generation records intended model tier choices and escalation rules in `artifacts/model_budget.json`.
4. Validation decides pass or blocked.
5. Source_generation writes a Librarian experience record and recipe candidate.
6. Later Librarian retrieval can surface the record for similar source_generation/library-first requests.

## Success State

The operator can inspect budget and experience artifacts without reading provider logs.

## Failure State

If source_generation blocks, the experience record preserves first blocker, failed checks, library plan, and file manifest references for future repair prompts.

## User-Visible Evidence

The source_generation report references model budget and Librarian experience artifacts.
