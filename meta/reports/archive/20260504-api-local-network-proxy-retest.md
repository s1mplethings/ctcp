# Demo Report - API Local Network Proxy Retest

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `llm_core/clients/openai_compatible.py`
- `tools/providers/api_agent.py`
- external run `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-111854-823548-orchestrate`

## Plan
1. Detect local proxy.
2. Run small API code-output probe through proxy.
3. Run formal API-only VN generation through proxy.
4. Inspect provider ledger and first blocker.

## Changes
- Added/closed proxy retest queue and task metadata.
- Recorded proxy test report and task archive.

## Verify
- Local proxy detected: `127.0.0.1:7890`, FlClash running.
- Small proxy-routed API probe passed and returned valid JSON with `main.py`.
- Formal proxy-routed run: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-111854-823548-orchestrate`.
- Provider ledger: `api_agent` executed early chair stages; `fallback_count=0`.
- First blocker: `contract_guardian/review_contract`.
- first failure point evidence: missing `reviews/review_contract.md` after `contract_guardian/review_contract` API execution failed.
- Errors: Cloudflare 504 followed by Cloudflare 520 from `api.gptsapi.net`.
- minimal fix strategy evidence: switch to a more stable endpoint/model or reduce formal prompt size/backoff; do not use local templates or Ollama as success evidence.
- triplet runtime wiring command evidence: live proxy run proves env proxy -> orchestrator -> dispatch -> `api_agent` -> provider ledger is connected; `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was not rerun because no runtime wiring code changed.
- triplet issue memory command evidence: existing API long-call transport issue remains valid; `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was not rerun because no issue memory schema/code changed.
- triplet skill consumption command evidence: `.agents/skills/ctcp-workflow/SKILL.md` was consumed; `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was not rerun because no runtime skill loader changed.
- Passed: `.venv\Scripts\python.exe scripts\workflow_checks.py`.
- Failed: `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile doc-only`.
- First canonical verify failure: module protection rejected pre-existing out-of-scope dirty files `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, and `tests/test_runtime_wiring_contract.py`.

## Questions
- None.

## Demo
- 本机代理可用，小 API 探针成功。
- 正式流程仍被 `api.gptsapi.net` 源站/网关错误挡住。

## Integration Proof
- connected: proxy env reached the API client.
- accumulated: run artifacts recorded provider ledger and errors.
- consumed: artifact gate blocked without local fallback.
