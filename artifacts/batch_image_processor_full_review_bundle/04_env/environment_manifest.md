# environment_manifest.md

- OS: Microsoft Windows 10.0.26200
- Python: Python 3.12.3
- Node: v24.11.0
- Repo git commit: 03ac68cb41b3bb41217a05857d597eb810a43f3e
- Source run root: C:\Users\sunom\.ctcp\runs\ctcp\20260413-batch-image-processor-delivery
- D-drive bundle directory: D:\.c_projects\adc\ctcp\artifacts\batch_image_processor_full_review_bundle
- D-drive bundle zip: D:\.c_projects\adc\ctcp\artifacts\batch_image_processor_full_review_bundle.zip
- Project entrypoint: app.py
- Project default URL: http://127.0.0.1:5085
- Project dependencies: Flask==3.1.2, Pillow==11.1.0
- Screenshot tooling used during original run: Playwright Chromium

## Run Commands
- Project start: `python app.py --serve`
- Project smoke: `python scripts/smoke_test.py`
- Virtual delivery E2E: `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
- SimLab lite: `python simlab/run.py --suite lite`
- Canonical verify: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`

## Key Artifact Paths
- Project package: `01_project/batch_image_processor.zip`
- Project directory copy: `01_project/project_dir`
- Final screenshot: `02_images/final-ui.png`
- Replay screenshot: `02_images/replayed_screenshot.png`
- Delivery manifest: `03_delivery/support_public_delivery.json`
- Replay report: `03_delivery/replay_report.json`
- Workflow log: `05_reports/workflow_checks.log`
- Verify log: `05_reports/verify_repo.log`
