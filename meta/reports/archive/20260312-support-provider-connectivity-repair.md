# Demo Report - Archive

## Topic

- Queue Item: `ADHOC-20260312-support-provider-connectivity-repair`
- Date: 2026-03-12
- Topic: 修复 support bot provider 连通性与兜底链路
- Status: `done`

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `docs/10_team_mode.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_support_bot.py`
- `tools/providers/ollama_agent.py`
- `tools/providers/api_agent.py`
- `scripts/externals/openai_responses_client.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_api_agent_templates.py`
- `tests/test_openai_responses_client_resilience.py`
- `tests/test_ollama_agent.py`
- `tests/test_runtime_wiring_contract.py`

### Plan
1. 对齐 CURRENT/LAST 与 queue binding。
2. 修 support provider fallback、Ollama support reply path、external API credentials 解析。
3. 跑 targeted tests、triplet guards 和 live smoke。
4. 跑 canonical verify，记录首个失败点或 PASS。

### Changes
- `scripts/ctcp_support_bot.py`
  - support provider 候选链现在会把 `manual_outbox` 当成真实 fallback，并消费 `outbox_created/outbox_exists` 等 deferred 状态。
- `tools/providers/ollama_agent.py`
  - support reply 现在优先走 Ollama 原生 `/api/chat`，不再复用 OpenAI-compatible chat path。
- `tools/providers/api_agent.py`
  - external API readiness 现在会忽略会遮蔽 notes 凭证的占位 `OPENAI_API_KEY=ollama`。
- `scripts/externals/openai_responses_client.py`
  - 真实 API 调用的 credential 解析与 readiness 规则对齐，避免 placeholder key 打到错误的 provider。
- `ai_context/problem_registry.md`
  - 记录 support bot provider 串联失败与 placeholder credentials 遮蔽的 issue-memory 条目。
- `tests/test_support_bot_humanization.py`
  - 新增 support bot fallback 到 deferred/manual-outbox-style reply 的回归。
- `tests/test_ollama_agent.py`
  - 新增 support reply 走原生 Ollama `/api/chat` 的回归。
- `tests/test_api_agent_templates.py`
  - 新增占位 env key 回退到 notes credentials 的回归。
- `tests/test_openai_responses_client_resilience.py`
  - 新增 placeholder `ollama` key 不再遮蔽 notes credentials 的回归。
- `meta/backlog/execution_queue.json`
  - 绑定并收口 `ADHOC-20260312-support-provider-connectivity-repair`。
- `meta/tasks/CURRENT.md`
  - 切到 provider-connectivity repair task truth，并回填完成态验证证据。
- `meta/reports/LAST.md`
  - 回填最新 gate-readable report summary。

### Verify
- initial blocker:
  - `python scripts\workflow_checks.py` => `1`
  - first failure point: `meta/reports/LAST.md` 缺少显式 `first failure` / `minimal fix strategy` 证据字段
  - minimal fix strategy:
    - 在 `meta/reports/LAST.md` 的 Verify 段补充首个失败点和最小修复策略的显式记录
- fix loop:
  - 更新 `meta/reports/LAST.md` / `meta/reports/archive/20260312-support-provider-connectivity-repair.md`，补齐 workflow gate 要求的显式证据词
- `python -m py_compile scripts/ctcp_support_bot.py tools/providers/api_agent.py tools/providers/ollama_agent.py scripts/externals/openai_responses_client.py tests/test_support_bot_humanization.py tests/test_api_agent_templates.py tests/test_openai_responses_client_resilience.py tests/test_ollama_agent.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (7 passed)
- `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (10 passed)
- `python -m unittest discover -s tests -p "test_openai_responses_client_resilience.py" -v` => `0` (5 passed)
- `python -m unittest discover -s tests -p "test_ollama_agent.py" -v` => `0` (4 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- live smoke:
  - `python scripts\externals\openai_agent_api.py` => `0` (`OK.`)
  - `python scripts\ctcp_support_bot.py --stdin --provider ollama_agent` => `0` (provider_status=`executed`; support reply artifact written)
  - `python scripts\ctcp_support_bot.py --stdin --provider api_agent` => `0` (provider_status=`executed`; support reply artifact written)
  - `python scripts\ctcp_support_bot.py --stdin --provider codex_agent` => `0` (provider_status=`outbox_created`; customer-facing deferred reply written)
- `python scripts\workflow_checks.py` => `0`
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1` => `0`

### Questions
- None.

### Demo
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- support session smoke root: `%TEMP%\ctcp_live_support_runs\ctcp\support_sessions\`

### Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `scripts/ctcp_support_bot.py`, `tools/providers/ollama_agent.py`, `tools/providers/api_agent.py`, `scripts/externals/openai_responses_client.py`
- downstream: `build_final_reply_doc()` -> `artifacts/support_reply.json` -> stdin/Telegram user-visible reply
- source_of_truth: support session dispatch config + provider output artifacts + env/notes credentials
- fallback: provider deferred states fall back to customer-facing manual-outbox-style reply instead of raw model-unavailable wording
- acceptance_test: targeted regressions + triplet guard + live smoke + `scripts/verify_repo.ps1`
- forbidden_bypass: prompt-only wording patch without wiring fixes
- user_visible_effect: support bot can keep replying when live model routes fail and no longer loses external credentials behind the placeholder `ollama` key
