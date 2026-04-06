# Demo Report - LAST

## Archived Topic

- Date: `2026-04-05`
- Topic: `Remove remaining legacy story-domain repo references`

## Outcome

- Active-surface legacy wording was removed from tests/current task-report state.
- Queue/archive labels were sanitized where archive policy permitted edits.
- Disposable runtime/generated artifacts were deleted.
- Focused frontend/integration regressions passed.
- Canonical verify no longer failed on the cleanup itself; the first remaining blocker was the pre-existing telegram runtime wiring permission failure under `%LocalAppData%`.

## Reason For Archive

- The repository focus is being shifted from wording cleanup to a structural product-mainline refactor:
  - `goal -> ProjectIntent -> Spec -> Scaffold -> Core Feature -> Smoke Run -> Delivery`
