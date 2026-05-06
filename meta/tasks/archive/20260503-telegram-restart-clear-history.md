# Task Archive - Telegram Restart Clear History

## Queue Binding

- Queue Item: `ADHOC-20260503-telegram-restart-clear-history`
- Date Closed: `2026-05-03`
- Lane: Delivery Lane
- Status: done

## Scope

- Clear Telegram support bot local session history on normal restart.
- Drop pending Telegram updates on normal restart.
- Do not delete generated project runs, credentials, or provider configuration.

## Changes

- Added `clear_telegram_support_history()` and `telegram_support_sessions_root()` to `scripts/ctcp_support_bot.py`.
- Wired `run_telegram_mode()` to clear history by default before polling.
- Changed normal Telegram startup to call `deleteWebhook(drop_pending_updates=True)`.
- Added `--keep-history` as an explicit diagnostic bypass.
- Added `tests/test_support_bot_telegram_restart.py`.
- Updated `docs/03_quality_gates.md`.

## Verify

- `python -m py_compile scripts\ctcp_support_bot.py tests\test_runtime_wiring_contract.py tests\test_support_bot_telegram_restart.py` passed.
- `python tests\test_support_bot_telegram_restart.py` passed.
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` passed.
- `python scripts\workflow_checks.py` passed.
- `python scripts\module_protection_check.py` passed.
- `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` passed.

## Runtime Restart Evidence

- Old bot process pair stopped: `20400` / `34512`.
- First restart attempt failed on `D:\ctcp_runs` access denied.
- Restarted with `CTCP_RUNS_ROOT=C:\Users\sunom\AppData\Local\Temp\ctcp_runs`.
- Current bot process pair: `540` / `7956`.
- Startup log confirms support session history cleanup count: `1`.
