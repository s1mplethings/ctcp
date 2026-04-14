# Task / Spec / Plan

## Active Queue Item
- `ADHOC-20260413-csv-cleaner-full-review-bundle`
- Layer/Priority: `L1 / P0`

## Fixed Project Brief
- Project: `CSV 数据清洗与导出 Web 工具`
- Delivery shape: `web_first`
- Runtime target: local browser-based Python web app
- Packaging target: project zip + support delivery manifest + cold replay artifacts

## Execution Plan Used
1. Rebind CTCP task to one dedicated real-project rehearsal topic.
2. Materialize a real CSV cleaner web project under one external run_dir.
3. Run project-local smoke and capture a high-value finished screenshot.
4. Emit `support_public_delivery.json` and packaged zip through the virtual delivery path.
5. Run cold replay against the final zip and persist `replay_report.json` + `replayed_screenshot.png`.
6. Run requested repo-level checks and keep pass/fail outputs.
7. Build one reviewer-facing bundle with project, evidence, env, and reports.
