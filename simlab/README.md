# SimLab

SimLab is a zero-GUI, zero-compile scene replay runner for deterministic workflow checks.

## Run

```powershell
python simlab/run.py --suite all
```

Optional outputs:

```powershell
python simlab/run.py --suite core --runs-root simlab/_runs --json-out simlab/_runs/last_summary.json
```

## Scene format

Each scene is a `.yaml` file (JSON subset is accepted). Supported step types:

- `run`: execute command and assert exit code
- `write`: write/append file content
- `expect_path`: assert file exists/does not exist
- `expect_text`: assert file includes/excludes strings
- `expect_bundle`: assert failure bundle existence

Run-step keys:

- `cmd` (required)
- `cwd` (optional, default `.`)
- `expect_exit` (`0`, non-zero int, or `"nonzero"`)
- `expect_output_includes` (optional)
- `bundle_on_nonzero` (optional)

## Output

Every run creates `simlab/_runs/<run_id>/`:

- `<scenario>/TRACE.md`
- `<scenario>/logs/*`
- `<scenario>/diff.patch` (on failure/bundle)
- `<scenario>/artifacts/*` (snapshots)
- `<scenario>/failure_bundle.zip` (when generated)
- `summary.json`

