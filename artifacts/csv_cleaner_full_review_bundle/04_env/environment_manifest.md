# Environment Manifest

- OS: Microsoft Windows 11 专业工作站版 10.0.26200 64 位
- Repo root: `D:\.c_projects\adc\ctcp`
- External run dir: `C:\Users\sunom\.ctcp\runs\ctcp\20260413-csv-cleaner-review`
- Python: `Python 3.12.3`
- Python executable: `D:\anaconda\python.exe`
- Node: `v24.11.0`
- Key project dependencies: Python standard library only for the delivered project (`http.server`, `csv`, `json`); Playwright was used only for screenshot capture during this review run.
- Current git commit: `03ac68cb41b3bb41217a05857d597eb810a43f3e`

## Commands Used
- Project run: `python app.py`
- Project replay/health: `python scripts/run_project_web.py --serve`
- Project replay/export: `python scripts/run_project_web.py --goal "replay smoke export" --project-name "CSV Cleaner Studio" --out generated_output`
- Project local tests: `python -m unittest discover -s tests -p "test_*.py" -v`
- Project local verify: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- Repo workflow check: `python scripts/workflow_checks.py`
- Repo virtual delivery E2E: `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
- Repo simlab lite: `python simlab/run.py --suite lite`
- Repo verify: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`

## Key Artifact Paths
- Final project zip: `C:\Users\sunom\.ctcp\runs\ctcp\20260413-csv-cleaner-review\artifacts\support_exports\csv-cleaner-web-tool.zip`
- Final screenshot: `C:\Users\sunom\.ctcp\runs\ctcp\20260413-csv-cleaner-review\project_output\csv-cleaner-web-tool\artifacts\screenshots\final-ui.png`
- Delivery manifest: `C:\Users\sunom\.ctcp\runs\ctcp\20260413-csv-cleaner-review\artifacts\support_public_delivery.json`
- Replay report: `C:\Users\sunom\.ctcp\runs\ctcp\20260413-csv-cleaner-review\artifacts\delivery_replay\replay_artifacts\replay_report.json`
- Replay screenshot: `C:\Users\sunom\.ctcp\runs\ctcp\20260413-csv-cleaner-review\artifacts\delivery_replay\replay_artifacts\replayed_screenshot.png`
- Review bundle root: `D:\.c_projects\adc\ctcp\artifacts\csv_cleaner_full_review_bundle`
- Review bundle zip: `D:\.c_projects\adc\ctcp\artifacts\csv_cleaner_full_review_bundle.zip`
