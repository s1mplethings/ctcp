# Reference Project Scaffold

`ctcp_orchestrate scaffold` generates a new project skeleton from curated CTCP templates.

## Command

```powershell
python scripts\ctcp_orchestrate.py scaffold `
  --out D:\work\my_new_proj `
  --name my_new_proj `
  --profile minimal
```

## CLI
- `--out <path>`: required output directory. Must resolve outside current CTCP repo root.
- `--name <project_name>`: optional. Defaults to output directory name.
- `--profile minimal|standard|full`: scaffold profile (`minimal` default).
- `--force`: allow regenerate into an existing output directory.
- `--runs-root <path>`: optional scaffold evidence root. Defaults to `CTCP_RUNS_ROOT`, else `simlab/_runs`.

## Profile Differences
- `minimal`: doc-first + verify skeleton only.
- `standard`: minimal + behavior index, artifact contracts, workflow registry sample, simlab sample scenario.
- `full`: standard + AI contract baseline, quality gates doc, workflow check helper, specs/tests placeholders.

## Safety Rules
- Template source is fixed: `templates/ctcp_ref/`.
- No dynamic copy from current working tree.
- `--out` inside current repo is rejected.
- `--force` only removes files listed by previous/generated manifest inside `--out`.

## Outputs
- In `--out`:
  - scaffolded files
  - `manifest.json` (generated file inventory)
  - `TREE.md` (generated tree listing)
- In scaffold run_dir:
  - `TRACE.md`
  - `artifacts/scaffold_plan.md`
  - `artifacts/scaffold_report.json`

## Validation
- Scaffold validates required paths (`README`, `docs`, `meta`, `scripts`).
- Manifest paths are checked for existence after generation.
- If a local verify entrypoint exists in scaffold output, scaffold runs it and records result in report.
