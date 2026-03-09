# Problem Registry (Reusable Template + Examples)

Purpose:
- Capture recurring failure patterns as reusable institutional memory.
- Keep entries short, reproducible, and directly actionable.

When to add:
- Same class of failure appears >= 2 times.
- A failure required non-obvious debugging steps.
- A policy mismatch caused avoidable rework.

## Entry Template

- Symptom:
- Repro:
- Root cause:
- Fix:
- Prevention:
- Tags:

## Example 1

- Symptom:
  Agent/patch claims "verified" but no reproducible evidence artifacts exist.
- Repro:
  Run build/test manually without saving structured logs; output cannot be audited later.
- Root cause:
  Verification flow was fragmented and not tied to a hard gate entrypoint.
- Fix:
  Standardize on `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`; record command and result in `meta/reports/LAST.md`.
- Prevention:
  Treat missing verify evidence as FAIL in review.
- Tags:
  verify, gate, evidence, reproducibility

## Example 2

- Symptom:
  Docs claim rules that scripts do not enforce (contract drift).
- Repro:
  Compare `docs/03_quality_gates.md` against `scripts/verify_repo.*`; documented gate differs from actual executed gate list.
- Root cause:
  Documentation changed independently from gate scripts.
- Fix:
  Update docs to script-aligned behavior or implement missing gate in scripts in the same patch.
- Prevention:
  Every gate change must include paired doc update and a verify run record.
- Tags:
  docs, contract, drift, verify
