# B039 scaffold-pointcloud

## Reason
- Provide a deterministic way to generate a complete point-cloud project source tree from CTCP-owned templates.

## Behavior
- Trigger: `python scripts/ctcp_orchestrate.py scaffold-pointcloud --out ... --profile ...`.
- Inputs / Outputs: pointcloud template profile + tokens -> generated project files under `--out` and run_dir evidence.
- Invariants:
  - `artifacts/SCAFFOLD_PLAN.md` is written before any project source file is generated.
  - output safety policy: fail when `--out` exists unless `--force`; `--force` clears only inside `--out` and refuses filesystem root.
  - generated project includes `meta/manifest.json` listing generated relative file paths.
  - scaffold run writes `TRACE.md`, `events.jsonl`, dialogue artifacts, and `artifacts/scaffold_pointcloud_report.json`.

## Result
- Acceptance: generated point-cloud project contains required minimal/standard files and manifest-backed file list.
- Evidence: `scripts/ctcp_orchestrate.py`, `templates/pointcloud_project/*`, `tests/test_scaffold_pointcloud_project.py`.
- Related Gates: workflow_gate
