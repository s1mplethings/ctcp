# Demo Report - API VN Generation Retest

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- external run `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-104454-103863-orchestrate`

## Plan
1. Bind a fresh API-only VN generation retest task.
2. Create and advance a formal API-only run with local provider overrides cleared.
3. Inspect provider ledger, trace, retry logs, and source-generation artifacts.
4. Run a small direct API code-output probe to distinguish base connectivity from long source-generation reliability.
5. Record the first blocker and workflow evidence.

## Changes
- Added and closed `ADHOC-20260504-api-vn-generation-retest` in queue/task/report metadata.
- Added issue memory for repeated formal API source-generation transport failures on long calls.

## Verify
- API-only run: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-104454-103863-orchestrate`.
- Formal API env: `CTCP_FORMAL_API_ONLY=1`, `CTCP_TRUE_API_REQUIRED=1`, local provider overrides cleared.
- Provider ledger: `api_agent` with `external_api_used=true` executed chair plan/file_request/PLAN/freeze, contract review, cost review, and source_generation attempt; `fallback_count=0`.
- First blocker: `chair/source_generation` failed before `artifacts/source_generation_report.json` was written.
- Source-generation retry errors: Cloudflare 520, Cloudflare 504, and `[SSL: TLSV1_ALERT_PROTOCOL_VERSION]`.
- Direct small API code-output probe passed and returned valid JSON containing `main.py`.
- Passed: `.venv\Scripts\python.exe scripts\workflow_checks.py`.
- Failed: `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile doc-only`.
- First canonical verify failure: module protection rejected pre-existing out-of-scope dirty files `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, and `tests/test_runtime_wiring_contract.py`.
- minimal fix strategy evidence:
  - Do not restore local templates or use local provider output as API success.
  - Keep source-generation blocked when the API response does not materialize.
  - Next smallest repair is transport-side: split/shorten source-generation, increase conservative backoff, or use a stable endpoint/model for long JSON source bundles.
- triplet runtime wiring command evidence:
  - Live run evidence proves `scripts\ctcp_orchestrate.py` -> dispatch -> `api_agent` -> provider ledger -> source-generation artifact gate is connected.
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was not rerun because this task did not change runtime wiring code.
- triplet issue memory command evidence:
  - `ai/MEMORY/ISSUE_MEMORY.md` records this recurring formal API long-call transport failure.
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was not rerun because this task only appended a failure-memory entry.
- triplet skill consumption command evidence:
  - `.agents/skills/ctcp-workflow/SKILL.md` was consumed for the repo workflow.
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was not rerun because no runtime skill loader changed.

## Questions
- None.

## Demo
- API access is working for small code-output calls.
- Formal long source-generation is still blocked by current API/proxy transport reliability.

## Integration Proof
- connected: formal API-only dispatch selected `api_agent`.
- accumulated: run trace, provider ledger, retry logs, and issue memory captured the result.
- consumed: the orchestrator blocked on missing source-generation output instead of falling back to local templates.
