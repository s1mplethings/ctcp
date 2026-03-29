# Demo Report - 20260324-api-connectivity-project-wiring-check

## Topic

API 连通性与项目内接线可用性验证

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/TEMPLATE_LAST.md`
- `.agent_private/NOTES.md`
- `tools/providers/api_agent.py`
- `scripts/externals/openai_responses_client.py`
- `scripts/externals/openai_agent_api.py`
- `scripts/ctcp_support_bot.py`

## Plan

1. Bind one ADHOC queue item for this API validation topic.
2. Probe external API connectivity through repository OpenAI-compatible client.
3. Exercise project runtime path through `ctcp_support_bot --stdin --provider api_agent`.
4. Capture provider execution evidence from support session artifacts.
5. Run canonical verify and record first failing gate plus minimal repair path.

## Changes

- `meta/backlog/execution_queue.json`
  - Added `ADHOC-20260324-api-connectivity-project-wiring-check` and finalized status as `blocked` with evidence note.
- `meta/tasks/archive/20260324-api-connectivity-project-wiring-check.md`
  - Added bound task card and completed DoD/verify evidence.
- `meta/tasks/CURRENT.md`
  - Rebound active task pointer and synchronized task summary/evidence.
- `meta/reports/archive/20260324-api-connectivity-project-wiring-check.md`
  - Added this archive report.
- `meta/reports/LAST.md`
  - Repointed latest report pointer and summary to this topic.

## Verify

- `python -c "from scripts.externals.openai_responses_client import call_openai_responses; text, err = call_openai_responses(prompt='Reply with API_OK only.', model='gpt-4.1-mini', timeout_sec=60); print('RESULT=' + ('OK' if bool(text.strip()) else 'ERR')); print((text if text else err)[:400])"` -> `0`
  - key output: `RESULT=OK`, `API_OK`
- `echo 现在先做一个项目内API接线测试，目标是确认support路径能调用api_agent并返回可见回复。 | python scripts/ctcp_support_bot.py --stdin --chat-id api-connectivity-check --provider api_agent` -> `0`
  - key output: support reply text emitted successfully
- support runtime artifacts (`C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/api-connectivity-check/artifacts`)
  - `support_reply.json`: `provider=api_agent`, `provider_status=executed`
  - `support_session_state.json`: `provider_runtime_buffer.last_provider=api_agent`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `1` (from canonical verify triplet stage)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `not reached` (triplet stopped at runtime wiring failure)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `not reached` (triplet stopped at runtime wiring failure)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-1) -> `1`
  - first failure point: `workflow gate (workflow checks)` due to missing mandatory sections in `meta/tasks/CURRENT.md`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-2 after fix) -> `1`
  - first failure point: `triplet runtime wiring contract`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-3 after report sync) -> `1`
  - first failure point: `workflow gate` (`LAST.md` triplet command evidence missing) -> fixed in report update
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-4) -> `1`
  - first failure point: `triplet runtime wiring contract`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-5 final) -> `1`
  - first failure point: `triplet runtime wiring contract`
- first failing details (preexisting):
  - `frontend/response_composer.py` hint-bank `IndexError`
  - `scripts/ctcp_support_bot.py::run_stdin_mode` StringIO `.buffer` compatibility
    - Telegram poll lock cleanup `PermissionError`
    - fallback reply mojibake assertion mismatch
- minimal fix strategy:
  - In a separate scope-bound task, repair triplet runtime wiring defects above, then rerun canonical verify.

## Questions

- None.

## Demo

- API direct connectivity: pass (`API_OK`).
- In-project runtime usage: pass (`api_agent` executed in support project turn).
- Evidence paths:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/api-connectivity-check/artifacts/support_reply.json`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/api-connectivity-check/artifacts/support_session_state.json`

## Integration Proof

- upstream: user message -> `scripts/ctcp_support_bot.py::process_message`
- current_module: `scripts/externals/openai_responses_client.py` + support provider execution path
- downstream: `artifacts/support_reply.json.reply_text` and provider status persisted in session state
- source_of_truth: command exit codes + support session artifacts in external run_dir
- fallback: on API failure, report first failing gate and minimal repair; no out-of-scope code rewrite
- acceptance_test:
  - `python -c ... call_openai_responses ...`
  - `python scripts/ctcp_support_bot.py --stdin --provider api_agent ...`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - no mock-only API claim
  - no skipping project runtime invocation
  - no skipping canonical verify
- user_visible_effect: 用户可确认“API 目前可连，且已能在项目 support 路径实际使用”。
