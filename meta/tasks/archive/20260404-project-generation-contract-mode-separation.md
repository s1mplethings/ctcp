# Task Archive - project-generation-contract-mode-separation

Archived because the active topic moved from contract-only MD clarification to runtime/code alignment for the same rule set.

## Archive Summary

- Queue Item: `ADHOC-20260404-project-generation-contract-mode-separation`
- Archived On: `2026-04-04`
- Archived Reason: `docs/41_low_capability_project_generation.md` has already been updated, and the active work now shifts to making code paths obey the new production/benchmark split.

## Handoff

- Completed in archived task:
  - `docs/41_low_capability_project_generation.md` now separates production mode and benchmark/regression mode.
  - Effective `context_pack` consumption and layered gates are now part of the contract.
- Remaining gap for next task:
  - Runtime path still mixes benchmark VN behavior into production-facing generation logic.
  - Project type and delivery shape are not yet resolved at one explicit decision point.
  - Gate semantics in code still need to be aligned with structural/behavioral/result layering.
