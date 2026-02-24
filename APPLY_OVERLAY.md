# Apply CTCP Team Workflow Overlay

This overlay updates workflow docs + gates + tools to match the “autonomous project team agent” target.

## Apply

1) Unzip this overlay into your repo root (allow overwrite).

2) Generate a task:
```powershell
python scripts\ctcp_orchestrate.py new-run --goal "your goal"
```

3) Advance orchestrator:
```powershell
python scripts\ctcp_orchestrate.py advance --max-steps 16
```

4) Sync doc index once:
```powershell
python scripts\sync_doc_links.py
```

5) Verify:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1
```

## Notes
- verify_repo will fail until `meta/tasks/CURRENT.md` exists (this is intended).
