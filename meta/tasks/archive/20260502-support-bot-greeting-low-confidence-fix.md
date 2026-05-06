# Task Archive - Support Bot Greeting Low Confidence Fallback Fix

- Queue Item: `ADHOC-20260502-support-bot-greeting-low-confidence-fix`
- Date: `2026-05-02`
- Lane: Delivery Lane
- Status: done with canonical verify timeout noted

## Scope

- Fix support reply policy so `GREETING` / `SMALLTALK` turns with customer-ready provider replies are not rewritten into low-confidence fallback wording by stale project context or degraded provider metadata.

## Changes

- `frontend/support_reply_policy.py`
- `tests/test_support_reply_policy_regression.py`
- `ai/MEMORY/ISSUE_MEMORY.md`
- task/report metadata

## Evidence

- Regression added: `test_degraded_greeting_keeps_customer_ready_provider_reply_test`.
- Targeted support policy, support humanization, support-chain, runtime-wiring, workflow, module-protection, code-health checks passed.
- SimLab lite latest summary passed `15/15`.
- Telegram bot restarted with proxy and patched code.

## Verify Note

- First canonical code-profile verify failed at S00 because this task card missed `## Acceptance`.
- After repairing the task card, canonical code-profile verify rerun timed out after `900` seconds after lite replay had passed; no new failing gate was returned.
