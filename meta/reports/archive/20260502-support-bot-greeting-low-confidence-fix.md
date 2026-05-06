# Demo Report - Support Bot Greeting Low Confidence Fallback Fix

See `meta/reports/LAST.md` for the same run report content and command evidence.

## Summary

- Fixed greeting/smalltalk intent inference so a customer-ready provider greeting is not overwritten by low-confidence fallback truth from a degraded API path.
- Added regression coverage.
- Restarted the Telegram bot with proxy and new code.

## Verification

- `test_support_reply_policy_regression.py`: passed (`12` tests).
- `test_support_bot_humanization.py`: passed (`66` tests).
- `test_support_chain_breakpoints.py`: passed (`14` tests).
- `test_runtime_wiring_contract.py`: passed (`25` tests).
- workflow/module/code-health checks passed.
- simlab lite latest summary passed (`15/15`).
- canonical code-profile verify rerun timed out after `900` seconds after lite replay had passed; no new failing gate returned.
