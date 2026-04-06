# Task - remove-all-legacy-story-domain-references

## Archive Note

- Archived on `2026-04-05` because the active repo topic moved from residual wording cleanup to product-mainline restructuring around structured intent and real MVP generation.
- Original queue item: `ADHOC-20260405-remove-all-legacy-story-domain-references`
- Outcome summary:
  - active tests/current task-report state stopped exposing the legacy story-domain wording
  - queue/archive labels were neutralized where policy allowed
  - disposable runtime/generated artifacts were removed
  - focused frontend/integration regressions passed
  - canonical verify first remaining blocker was the pre-existing telegram runtime wiring permission failure

## Handoff

- Cleanup closure is complete enough to stop treating legacy wording as the main topic.
- Follow-on work should target the product mainline itself:
  - structured `ProjectIntent`
  - frontend intent modeling instead of shallow routing
  - backend MVP generation pipeline instead of artifact-first shell behavior
