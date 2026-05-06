# Task Archive - Support Bot Provider Router Split

## Queue Binding

- Queue Item: `ADHOC-20260502-support-bot-provider-router-split`
- Date: `2026-05-02`
- Status: `done`

## Scope

- Split support provider dispatch config/candidates and support mode-router helpers out of `scripts/ctcp_support_bot.py`.
- Keep runtime logic in Python modules, not Markdown.
- Preserve provider execution, support routing, project bridge, package delivery, and Telegram behavior.

## Results

- `scripts/ctcp_support_bot.py`: `5828` -> `5465`
- `scripts/ctcp_support_bot_provider.py`: `292`
- `scripts/ctcp_support_bot_mode_router.py`: `219`
- Initial `ctcp_support_bot_provider.py` was `489` lines, so mode-router logic was split into its own small module before closing.

## Verification

- `python -m py_compile scripts\ctcp_support_bot.py scripts\ctcp_support_bot_provider.py scripts\ctcp_support_bot_mode_router.py scripts\ctcp_support_bot_progress.py scripts\ctcp_support_bot_session_state.py scripts\ctcp_support_bot_session_normalize.py scripts\ctcp_support_bot_io.py scripts\ctcp_support_bot_constants.py scripts\ctcp_support_bot_text_patterns.py` passed.
- `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v` passed (`14` tests).
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` passed (`25` tests).
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` passed (`3` tests).
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` passed (`3` tests).
- `python scripts\workflow_checks.py` passed.
- `python scripts\module_protection_check.py` passed.
- `python scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile contract` passed.
- `git diff --check` passed with CRLF warnings only.
