# Demo Report - Telegram Restart Clear History

## Latest Report

- File: `meta/reports/archive/20260503-telegram-restart-clear-history.md`
- Date: `2026-05-03`
- Topic: `Telegram restart clear history`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_support_bot_io.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_telegram_restart.py`
- `docs/03_quality_gates.md`

### Plan
1. Bind a Delivery Lane task for Telegram restart history clearing.
2. Clear local Telegram support session directories before polling starts.
3. Drop pending Telegram updates on startup when history clearing is enabled.
4. Keep an explicit `--keep-history` diagnostic option for tests/manual debugging.
5. Add focused runtime regression coverage without growing oversized test files.
6. Verify, then restart the live Telegram bot.

### Changes
- `scripts/ctcp_support_bot.py` now clears `ctcp/support_sessions/*` under the external runs root at Telegram startup by default.
- Telegram startup now calls `deleteWebhook` with `drop_pending_updates=True` when restart-history clearing is enabled.
- `scripts/ctcp_support_bot.py telegram --keep-history` can explicitly preserve history for diagnostics; normal restart does not use it.
- `tests/test_support_bot_telegram_restart.py` proves stale local support session state is removed before polling.
- `docs/03_quality_gates.md` records the Telegram support restart history lint.

### Verify
- targeted command evidence:
  - `python -m py_compile scripts\ctcp_support_bot.py tests\test_runtime_wiring_contract.py tests\test_support_bot_telegram_restart.py` passed.
  - `python tests\test_support_bot_telegram_restart.py` passed (`1` test).
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` passed (`25` tests).
  - `python scripts\workflow_checks.py` passed.
  - `python scripts\module_protection_check.py` passed.
  - `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- first failure point evidence:
  - First runtime regression attempt grew oversized `tests/test_runtime_wiring_contract.py`; fixed by moving the new regression to `tests/test_support_bot_telegram_restart.py`.
  - First live restart failed because inherited `CTCP_RUNS_ROOT` pointed at `D:\ctcp_runs`, which returned access denied; fixed by starting the live bot with `CTCP_RUNS_ROOT` under the user temp directory.
- minimal fix strategy evidence:
  - Startup cleanup is limited to support session history, not generated project run directories or credentials.
  - Pending Telegram updates are dropped only on normal clean-history startup.
- triplet runtime wiring command evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` ran directly and during code-profile verify, and passed.
- triplet issue memory command evidence:
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` ran during code-profile verify and passed.
- triplet skill consumption command evidence:
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` ran during code-profile verify and passed.
- canonical verify evidence:
  - command: `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
  - result: passed, including lite ctest, workflow/protection/prompt/plan/patch/behavior/contract/doc/code-health/triplet/lane gates and `481` Python unit tests (`4` skipped).

### Questions
- None.

### Demo
- Live restart command used `scripts\ctcp_support_bot.py telegram --poll-seconds 15`.
- Live startup stderr confirmed: `telegram startup cleared support history: count=1 root=C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\support_sessions`.
- Current bot process pair: `540` / `7956`.
- Latest log files:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\support_bot_telegram_logs\telegram-20260503-104925.out.log`
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\support_bot_telegram_logs\telegram-20260503-104925.err.log`

### Integration Proof
- upstream: CLI `scripts\ctcp_support_bot.py telegram` calls `run_telegram_mode()`.
- current_module: `run_telegram_mode()` invokes `clear_telegram_support_history()` before polling and before proactive support cycles consume session state.
- downstream: new Telegram messages create fresh support sessions; old local support history and old pending updates are not consumed as the current turn.
- connected + accumulated + consumed:
  - connected: startup connects restart to support-session cleanup.
  - accumulated: cleanup reports the sessions root and cleared count to stderr.
  - consumed: regression and live restart both exercised the default clean-start behavior.
