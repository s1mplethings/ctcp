# Demo Report - Archive

## Topic

- Queue Item: `ADHOC-20260313-support-api-first-local-degrade`
- Date: 2026-03-13
- Topic: support 回复锁到 api_agent，并把项目 zip/截图直发链路接到 Telegram
- Status: `blocked`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/10_team_mode.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `agents/prompts/support_lead_reply.md`
- `docs/dispatch_config.support_bot.sample.json`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

### Plan
1. 对齐 queue/CURRENT/LAST/archive，锁定 API-first + local-only degrade 范围。
2. 调整 `scripts/ctcp_support_bot.py` 默认 provider、降级链和用户可见 failure wording。
3. 同步 docs/sample config/prompt contract。
4. 去掉 support lane 的 preset 问候/开场句，遇到 greeting 污染时先重试 API，再决定是否降级本地。
5. 把 Telegram `sendDocument/sendPhoto`、public delivery discovery 和 zip materialization 接起来，禁止继续口头承诺发邮箱。
6. 跑 targeted checks、triplet guards、workflow gate、canonical verify。

### Changes
- `scripts/ctcp_support_bot.py`
  - switched the default support reply path to `api_agent`
  - limited the normal customer-visible support reply chain to `api_agent -> ollama_agent`
  - treated mojibake / invalid / empty API replies as unusable and eligible for local degrade
  - added one guarded `api_agent` retry when greeting/smalltalk output leaks stale project context
  - removed support-lane fallback to preset greeting/intake entry text for greeting/smalltalk/project-intake turns
  - added truth-bound public delivery discovery for bound runs, zip materialization, and Telegram `sendDocument/sendPhoto` wiring
  - synthesized direct-send actions only when the current channel can send files and the bound project actually has package/screenshot artifacts
  - rewired zip requests so Telegram replies no longer ask for email when the file can be sent directly
  - injected API-failover context into the local fallback prompt and added explicit user-visible API-unavailable notice handling
  - removed the old fixed `没连上稳定的回复能力` / `我先帮你整理一下` shell from the normal support failure path
- `docs/10_team_mode.md`, `docs/dispatch_config.support_bot.sample.json`, `agents/prompts/support_lead_reply.md`
  - aligned the support lane contract and sample config to API-first plus local-only degrade, explicitly banned preset greeting shells, and documented direct Telegram artifact delivery
- `tests/test_support_bot_humanization.py`, `tests/test_runtime_wiring_contract.py`
  - added regressions for API-first default routing, stale greeting context -> API retry, invalid greeting reply -> local fallback, public delivery discovery, zip/sendDocument execution, and Telegram attachment wiring
- `ai_context/problem_registry.md`
  - recorded the new user-visible API-first/local-degrade regression class
- `meta/backlog/execution_queue.json`, `meta/tasks/CURRENT.md`, `meta/tasks/archive/20260313-support-api-first-local-degrade.md`, `meta/reports/LAST.md`, `meta/reports/archive/20260313-support-api-first-local-degrade.md`
  - bound the task and recorded the actual verify evidence

### Verify
- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => first run `1`
- first failure point:
  - `test_build_final_reply_doc_sanitizes_forbidden_raw_reply`
  - `test_support_bot_fallback_text_stays_customer_facing`
  - `test_process_message_api_override_degrades_to_local_on_unusable_api_reply`
- minimal fix strategy:
  - update the runtime so mojibake is treated as unusable API output that degrades to local, and align the old fallback-text tests to the new API-first/no-canned-fallback contract
- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => second run `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => second run `0` (23 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `python scripts/workflow_checks.py` => `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
  - first failure point: `patch check (scope from PLAN)`
  - failure detail: `generated_projects/story_organizer/README.md` is still reported out-of-scope by `scripts/patch_check.py` under the repo-wide current PLAN gate
  - minimal fix strategy: bind an explicit contract/scope update for `generated_projects/story_organizer/` or move delivery outputs out of the repo worktree before rerunning canonical verify; do not silently let Telegram delivery wiring widen patch scope

### Questions
- None.

### Demo
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `meta/tasks/archive/20260313-support-api-first-local-degrade.md`
- `meta/reports/archive/20260313-support-api-first-local-degrade.md`

### Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `scripts/ctcp_support_bot.py` plus support-lane contract docs/tests
- downstream: `support_provider_candidates()` -> `execute_provider()` -> `artifacts/support_reply.provider.json` -> `build_final_reply_doc()` -> `artifacts/support_reply.json`
- source_of_truth: support session `dispatch_config.json`, `support_prompt_input.md`, `support_reply.provider.json`, `support_reply.json`, `support_session_state.json`
- fallback: `api_agent` 失败时仅允许降级到本地 provider；若本地也失败，用户可见回复必须直接说明当前连不上
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass: prompt-only wording patch, keeping manual_outbox/codex in support-reply fallback, replacing one canned shell with another
- user_visible_effect: 正常客服回复默认来自 `api_agent`；如果用户在 Telegram 里明确要项目 zip/截图，且绑定 run 确实有真实 artifact，bot 会直接把文件发到当前对话，而不是继续口头承诺“稍后发邮箱”。
