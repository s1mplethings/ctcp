# Archived Task - Support Bot New Request Stale Result Fix

Archived from `meta/tasks/CURRENT.md` on `2026-05-02`.

- Queue Item: `ADHOC-20260502-support-bot-new-request-stale-result-fix`
- Status: done
- Summary: fresh project-create turns now supersede stale completed/PASS bound runs before support bridge sync records the turn; explicit result/status/package requests still reuse completed runs.
- Key evidence:
  - `tests/test_support_bot_stale_delivery_context.py`
  - `python -m unittest discover -s tests -p "test_support_bot_stale_delivery_context.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
