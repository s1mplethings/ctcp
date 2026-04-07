# ADLC Pipeline (Executable)

Scope boundary:

- This file describes runtime ADLC lane concepts.
- It is not the repository-purpose document.
- It is not the canonical repository modification flow document.
- Repo purpose source: `docs/01_north_star.md`.
- Canonical repository flow source: `docs/04_execution_flow.md`.
- Runtime truth/evidence contract source: `docs/00_CORE.md`.

This repository enforces an executable ADLC loop:

`doc -> analysis -> find -> plan -> build <-> verify -> contrast -> fix -> merge/deploy`

Default execution path is headless.

## Stage Outputs

1. `doc`
- Contracts/spec updates (`docs/*.md`, `specs/*.md`)
- Verify rules updated (`docs/verify_contract.md`)

2. `analysis`
- Problem statement and risks in task docs (`meta/tasks/CURRENT.md`)

3. `find`
- Reproducible command path and target files identified

4. `plan`
- Step list + acceptance in `meta/tasks/CURRENT.md`

5. `build <-> verify`
- Execute `scripts/verify_repo.sh` or `scripts/verify_repo.ps1`
- Produce canonical verify evidence `artifacts/verify_report.json` (run_dir) and step logs

6. `contrast`
- Compare two runs via `tools/contrast_proof.py`
- Output markdown report `contrast_report.md`

7. `fix`
- Apply minimal patch and rerun verify

8. `merge/deploy`
- Merge only if gate passes and evidence exists

## Gate Conditions

Hard gate:

- `python tools/adlc_gate.py --proof-dir <proof_dir>`

Fail conditions:

- Missing canonical verify report (`artifacts/verify_report.json`)
- Missing required logs
- Any required step non-zero
- `proof.result != PASS`

## CI Evidence

CI runs the same verify scripts and uploads `artifacts/verify/**`.
Evidence is the source of truth for pass/fail claims.
