# Decision Log (Reusable Template + Example)

Purpose:
- Record temporary exemptions, policy deviations, or risk-accepted choices.
- Ensure every deviation has owner, scope, and rollback/follow-up plan.

When required:
- Contract hard rule is bypassed or deferred.
- Migration compatibility is kept temporarily.
- Planned debt is accepted to unblock critical path.

## Entry Template

- Decision:
- Context:
- Why:
- Scope:
- Follow-up Plan:
- Owner:
- Date:

## Example

- Decision:
  Keep `verify_report.md` as optional compatibility output, while standardizing canonical verify artifact to `artifacts/verify_report.json`.
- Context:
  Existing downstream readers still consume markdown summaries.
- Why:
  Avoid breaking migration users while removing naming ambiguity in hard contract.
- Scope:
  Documentation and report tooling only; DoD gate authority unchanged.
- Follow-up Plan:
  Add migration notice in docs; remove compatibility path after consumers are upgraded.
- Owner:
  Chair/Planner
- Date:
  2026-03-07
