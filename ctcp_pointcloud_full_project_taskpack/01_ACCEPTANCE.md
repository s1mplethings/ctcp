# Acceptance Criteria

PASS if:
1) scaffold-pointcloud returns 0 and output project root contains required files + meta/manifest.json
2) cos-user-v2p returns 0 with stub_ok.zip and dialogue script and copies outputs to destination
3) Both commands produce CTCP run_dir evidence (doc-first plan + trace + dialogue + report)
4) CTCP verify_repo.ps1 passes after changes
