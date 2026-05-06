# Task Archive - Support Bot Reply Utils Split

- Date: `2026-05-02`
- Queue Item: `ADHOC-20260502-support-bot-reply-utils-split`
- Status: `done`
- Lane: `Delivery Lane`

## Scope

- Split reply text sanitization, language hints, code-dump detection, provider-doc sanitation, and provider reply validation helpers out of `scripts/ctcp_support_bot.py`.
- Keep runtime logic in Python modules, not Markdown.
- Preserve existing support bot behavior and import surface.

## Changes

- Added `scripts/ctcp_support_bot_reply_utils.py`.
- Updated `scripts/ctcp_support_bot.py` to import the extracted helper names.
- Fixed the extracted recovery import path to `scripts.ctcp_support_recovery`.

## Evidence

- `scripts/ctcp_support_bot.py`: `4226` -> `3582` lines.
- `scripts/ctcp_support_bot_reply_utils.py`: `403` lines.
- py_compile passed for support bot and extracted modules.
- `test_support_bot_humanization.py` passed (`66` tests).
- `test_support_chain_breakpoints.py` passed (`14` tests).
- `test_runtime_wiring_contract.py` passed (`25` tests).
- `test_issue_memory_accumulation_contract.py` passed (`3` tests).
- `test_skill_consumption_contract.py` passed (`3` tests).
- `python scripts\workflow_checks.py` passed.
- `python scripts\module_protection_check.py` passed.
- `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile contract` passed.
- `git diff --check` reported CRLF normalization warnings only.

## Closure

- Completion evidence is recorded in `meta/reports/LAST.md`.
- Report archive: `meta/reports/archive/20260502-support-bot-reply-utils-split.md`.
