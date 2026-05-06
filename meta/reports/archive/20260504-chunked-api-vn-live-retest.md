# Demo Report - Chunked API VN Live Retest

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- external run `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-124049-309194-orchestrate`

## Plan
1. Create fresh formal API-only VN run.
2. Advance with proxy and chunking enabled.
3. Inspect first blocker and provider evidence.

## Changes
- Added and closed live retest task/report metadata.

## Verify
- Run: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-124049-309194-orchestrate`.
- Provider ledger: early chair stages used `api_agent`, `fallback_count=0`.
- first failure point evidence: `contract_guardian/review_contract` failed before writing `reviews/review_contract.md`.
- Errors: Cloudflare 520 on first attempt, Cloudflare 504 on retry, both from `api.gptsapi.net`.
- `artifacts/source_generation_report.json` was not written, so chunked source-generation was not reached.
- minimal fix strategy evidence: add review-stage retry/backoff or smaller review prompts, or switch to a stable endpoint; do not use local fallback as success.
- triplet runtime wiring command evidence: live run proves orchestrator -> dispatch -> `api_agent` -> provider ledger is connected; `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was not rerun.
- triplet issue memory command evidence: existing API transport issue still applies; `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was not rerun.
- triplet skill consumption command evidence: `.agents/skills/ctcp-workflow/SKILL.md` was consumed; `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was not rerun.
- Passed:
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
- Failed:
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile doc-only`
  - first canonical verify failure: module protection rejected pre-existing out-of-scope dirty files `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, and `tests/test_runtime_wiring_contract.py`.

## Questions
- None.

## Demo
- The fresh retest did not reach chunked source generation because review-stage API transport failed first.

## Integration Proof
- connected: fresh VN goal reached formal API-only provider dispatch.
- accumulated: trace, ledger, status, and stderr captured the first blocker.
- consumed: orchestrator blocked without local fallback.
