# B037 scaffold-reference-project

## Reason
- Provide a deterministic way to bootstrap a new project from a curated CTCP reference template.

## Behavior
- Trigger: `python scripts/ctcp_orchestrate.py scaffold --out ... --profile ...`.
- Inputs / Outputs: template profile manifest + tokens -> generated project files under `--out`.
- Invariants:
  - template source is fixed at `templates/ctcp_ref/` (no dynamic repo copy).
  - scaffold blocks `--out` paths inside current repo root.
  - `--force` only removes previously generated/template-listed files inside `--out`.
  - scaffold run writes evidence to run_dir (`TRACE.md`, `artifacts/scaffold_plan.md`, `artifacts/scaffold_report.json`).

## Result
- Acceptance: scaffold produces manifest-backed file tree and validation report.
- Evidence: `scripts/ctcp_orchestrate.py`, `tools/scaffold.py`, `templates/ctcp_ref/*`.
- Related Gates: workflow_gate
