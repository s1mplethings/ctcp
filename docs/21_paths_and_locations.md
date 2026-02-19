# Paths And Locations

本文件定义 CTCP 路径权威规则。默认运行产物必须在仓库外部。

## Canonical path policy

| Scope | Location | Rule |
|---|---|---|
| External runs root | `${CTCP_RUNS_ROOT}` | MUST use env value if set |
| External runs root fallback | `~/.ctcp/runs` | MUST use when env not set |
| Repo slug | `<repo root dir name>` | MUST be auto-derived and normalized |
| Run dir | `<runs_root>/<repo_slug>/<run_id>/` | MUST hold actual run artifacts |
| Repo pointers | `meta/run_pointers/` | MUST hold lightweight pointer files only |

## Repo-internal vs repo-external

Repo-internal (allowed):
- `docs/`, `specs/`, `meta/tasks/`, `meta/reports/`
- `meta/paths.json`
- `meta/run_pointers/LAST_RUN.txt`
- optional lightweight pointers (`LAST_TRACE.txt`, `LAST_QUESTIONS.txt`)

Repo-external (must be outside repo by default):
- `TRACE.md`
- `PROMPT.md`
- `QUESTIONS.md`
- run-level `artifacts/*`
- `logs/*`
- `failure_bundle.zip`
- full run package directory

Deprecated default locations (do not use as default output):
- `meta/runs/`
- `simlab/_runs/`

## Environment setup examples

Windows PowerShell:

```powershell
$env:CTCP_RUNS_ROOT = "$HOME\\.ctcp\\runs"
python tools\ctcp_team.py start "smoke goal"
```

Linux/macOS bash:

```bash
export CTCP_RUNS_ROOT="$HOME/.ctcp/runs"
python tools/ctcp_team.py start "smoke goal"
```

## Notes

- `verify_repo` replay paths are gate-specific exceptions and may remain repo-local.
- This policy changes default output location only; command interfaces stay stable.
