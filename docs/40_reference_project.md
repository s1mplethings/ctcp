# Reference Project Scaffold

`ctcp_orchestrate scaffold` and `ctcp_orchestrate scaffold-pointcloud` support two source modes:

- `template` (default, backward-compatible)
- `live-reference` (controlled export from current CTCP repo)

## Commands

### scaffold

```powershell
python scripts\ctcp_orchestrate.py scaffold `
  --out D:\work\my_new_proj `
  --name my_new_proj `
  --profile minimal `
  --source-mode template
```

```powershell
python scripts\ctcp_orchestrate.py scaffold `
  --out D:\work\my_new_proj `
  --name my_new_proj `
  --profile minimal `
  --source-mode live-reference
```

### scaffold-pointcloud

```powershell
python scripts\ctcp_orchestrate.py scaffold-pointcloud `
  --out D:\v2p_projects\demo_v2p `
  --name demo_v2p `
  --profile minimal `
  --source-mode template `
  --runs-root D:\ctcp_runs
```

```powershell
python scripts\ctcp_orchestrate.py scaffold-pointcloud `
  --out D:\v2p_projects\demo_v2p `
  --name demo_v2p `
  --profile minimal `
  --source-mode live-reference `
  --runs-root D:\ctcp_runs
```

## CLI (common)
- `--out <path>`: required output directory. Must resolve outside current CTCP repo root.
- `--name <project_name>`: optional. Defaults to output directory name.
- `--profile`:
  - scaffold: `minimal|standard|full` (`minimal` default)
  - scaffold-pointcloud: `minimal|standard` (`minimal` default)
- `--source-mode template|live-reference`: source mode (`template` default).
- `--force`: allow regenerate into an existing output directory.
- `--runs-root <path>`: optional run evidence root. Defaults to `CTCP_RUNS_ROOT`, else `simlab/_runs`.

## Source Mode Semantics

### template
- Keeps existing behavior.
- `scaffold` uses curated files from `templates/ctcp_ref/`.
- `scaffold-pointcloud` uses curated files from `templates/pointcloud_project/`.

### live-reference
- Reads `meta/reference_export_manifest.yaml` and exports only listed whitelist entries.
- Export source is the current CTCP repo revision (not static bundle only).
- Supports profile-specific export sets (`minimal|standard|full`, and pointcloud profiles).
- Writes generation provenance metadata including source commit.

## Live-Reference Safety Boundary

`meta/reference_export_manifest.yaml` is the only whitelist truth source for live-reference export.

Hard rules:
- Paths in export manifest are repo-root relative paths only.
- All source/target paths are normalized and checked for traversal.
- Export is allowlist-based only; no whole-repo walk+blacklist mode.
- Always excludes `.git`, runtime/cache/build/output paths (for example `runs/`, `out/`, `fixture/`, `__pycache__/`, `.pytest_cache`, build dirs).
- `--out` inside current repo is rejected.
- `--force` only removes files governed by existing generated manifest; unknown files block regeneration.

## Generated Metadata

Live-reference output includes `meta/reference_source.json` with:
- `source_repo` or `source_root_hint`
- `source_commit` (`unknown` when git commit cannot be resolved)
- `source_mode`
- `export_manifest`
- `generated_at`
- `profile`
- optional command summary
- `inherited_copy`
- `inherited_transform`
- `generated_files`

Generated manifest is also extended to include source/export inventory fields:
- `files`
- `generated`
- `inherited_copy`
- `inherited_transform`
- `excluded`
- `source_commit`
- `source_mode`

## Run Evidence

Scaffold run artifacts remain:
- `TRACE.md`
- `events.jsonl`
- `artifacts/scaffold_plan.md` or `artifacts/SCAFFOLD_PLAN.md`
- `artifacts/scaffold_report.json` or `artifacts/scaffold_pointcloud_report.json`

For live-reference, reports additionally record:
- `source_mode`
- `source_commit`
- `export_manifest_path`
- `inherited_copy_count`
- `inherited_transform_count`

## Downstream Compatibility

Generated projects remain CTCP-style contract projects and can continue with:
- project-local `scripts/verify_repo.ps1` / `scripts/verify_repo.sh` (if present in generated project)
- `cos-user-v2p` (pointcloud project flow)
- repository `new-run / advance` orchestration in normal CTCP execution chain
