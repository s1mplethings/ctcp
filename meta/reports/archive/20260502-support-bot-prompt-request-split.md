# Report Archive - Support Bot Prompt Request Split

- Date: `2026-05-02`
- Topic: `Support bot prompt request split`
- Queue Item: `ADHOC-20260502-support-bot-prompt-request-split`

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-patch-guard/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_support_bot_prompting.py`

## Plan

1. Bind a ninth narrow support-bot slimming task.
2. Extract support prompt template/context assembly and support request construction into a small Python module.
3. Preserve helper names through the `scripts.ctcp_support_bot` import surface.
4. Run targeted prompt/reply regressions, workflow checks, module protection, code health, and verify entrypoint.

## Changes

- Added `scripts/ctcp_support_bot_prompting.py`.
- Moved support prompt template, prompt context assembly, project prompt context, failover/repair prompt assembly, and support provider request payload construction out of `scripts/ctcp_support_bot.py`.
- Kept Markdown limited to task/report metadata.

## Verify

- first failure point evidence:
  - no failing gate after extraction.
- minimal fix strategy evidence:
  - no repair was needed after extraction; prompt/request helper names remained exported through `scripts.ctcp_support_bot`.
- `scripts/ctcp_support_bot.py`: `3582` -> `3264` lines.
- `scripts/ctcp_support_bot_prompting.py`: `359` lines.
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

## Questions

- None.

## Demo

- Prompt/request behavior now lives in a small Python module.
- Main support bot file is smaller with no intended behavior change.

## Integration Proof

- connected: `scripts/ctcp_support_bot.py` imports helper names from `scripts/ctcp_support_bot_prompting.py`.
- accumulated: prompt/request construction helpers are grouped in a runtime module.
- consumed: targeted support/runtime regressions, workflow, module protection, code health, and contract verify consumed the new module surface.
