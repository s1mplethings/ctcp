# Task Archive

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done`

## Active Task

- Queue Item: `ADHOC-20260312-support-provider-connectivity-repair`
- Date: 2026-03-12
- Topic: 修复 support bot provider 连通性与兜底链路
- Status: `done`

## Context

- Why this item now?
  用户在 2026-03-11 23:48 的 support bot 会话中发送真实项目需求后，provider 链连续失败并回到“暂时还没连上稳定的回复能力”。
- Dependency check:
  - `ADHOC-20260310-support-customer-visible-de-mechanicalization`: `done`
  - `ADHOC-20260311-telegram-run-provider-alignment`: `done`
  - `ADHOC-20260311-support-bot-humanization-verify-blocker`: `done`
- Scope boundary:
  - 只修 support bot reply provider 连通性、fallback、provider readiness 与对应 regression。
  - 不扩到 frontend PM 文案全面重写，也不改 orchestrator/bridge 状态机。

## Task Truth Source

- task_purpose:
  修复 `scripts/ctcp_support_bot.py` 的 support reply provider 链，让本地 Ollama、外部 API、codex/manual_outbox fallback 都能落到真实可消费的 `support_reply.json`，不再因为 provider 串联失败直接回到统一“模型不可用”兜底。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py` 可调整 support provider 候选顺序、fallback 逻辑与 deferred reply 处理。
  - `tools/providers/ollama_agent.py` 可为 support reply 引入 Ollama 原生 `/api/chat` 路径。
  - `tools/providers/api_agent.py` 与 `scripts/externals/openai_responses_client.py` 可收紧占位凭证解析，避免 `OPENAI_API_KEY=ollama` 遮蔽真实 notes 凭证。
  - `tests/test_support_bot_humanization.py`、`tests/test_ollama_agent.py`、`tests/test_api_agent_templates.py`、`tests/test_openai_responses_client_resilience.py` 可补最小 regression。
  - `ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录本轮证据。
- forbidden_goal_shift:
  - 不把这轮扩大成 support bot 全量提示词/文案重写。
  - 不通过硬编码固定回复绕过 provider 连通性问题。
  - 不改 CTCP frontend bridge / orchestrator / dispatch 主流程来掩盖 support reply provider 缺陷。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `tools/providers/ollama_agent.py`
  - `tools/providers/api_agent.py`
  - `scripts/externals/openai_responses_client.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_ollama_agent.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_openai_responses_client_resilience.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `frontend/*`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `tools/telegram_cs_bot.py`
  - 与“删除旧 Telegram bot”相关的其他未提交工作树改动
- completion_evidence:
  - support provider 候选链会把 `manual_outbox` 作为真实 fallback，而不是只在全失败后回“模型不可用”。
  - `ollama_agent` 对 support reply 走原生 `/api/chat` 并能在 live smoke 中返回 `support_reply.json`。
  - `api_agent` 在 `OPENAI_API_KEY=ollama` 占位 env 存在时，仍能回退到本机 notes 中的真实外部 API 凭证。
  - targeted regressions、triplet guard 通过；若 canonical verify 失败，记录首个失败点与最小修复策略。

## Analysis / Find

- Entrypoint analysis:
  - support 会话入口为 `scripts/ctcp_support_bot.py::process_message`。
- Downstream consumer analysis:
  - provider 结果会写入 `artifacts/support_reply.provider.json`，随后 `build_final_reply_doc()` 归一化为用户可见 `artifacts/support_reply.json`。
- Source of truth:
  - support session `artifacts/dispatch_config.json`
  - `artifacts/support_reply.provider.json`
  - `artifacts/support_reply.json`
  - 进程 env 与 `.agent_private/NOTES.md`
- Current break point / missing wiring:
  - `support_provider_candidates()` 没把 `manual_outbox` 作为真实 fallback。
  - `process_message()` 忽略 `outbox_created/outbox_exists` 等 deferred provider 状态。
  - `ollama_agent` 对 support reply 仍走 OpenAI-compatible path，触发 `does not support chat`。
  - `api_agent` / `openai_responses_client` 让占位 `OPENAI_API_KEY=ollama` 抢先覆盖了本机 notes 凭证。
- Repo-local search sufficient: `yes`

## Integration Check

- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `scripts/ctcp_support_bot.py`, `tools/providers/ollama_agent.py`, `tools/providers/api_agent.py`, `scripts/externals/openai_responses_client.py`
- downstream:
  `build_final_reply_doc()` -> `artifacts/support_reply.json` -> stdin/Telegram 用户可见回复
- source_of_truth:
  support session `dispatch_config.json` + provider output artifacts + external credential resolution (`env` / `.agent_private/NOTES.md`)
- fallback:
  优先尝试 `ollama_agent -> api_agent -> codex_agent`；无可用即时回复时退回 `manual_outbox` deferred reply，保持 customer-facing 文案，不暴露 raw provider 错误。
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tools/providers/api_agent.py tools/providers/ollama_agent.py scripts/externals/openai_responses_client.py tests/test_support_bot_humanization.py tests/test_api_agent_templates.py tests/test_openai_responses_client_resilience.py tests/test_ollama_agent.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_openai_responses_client_resilience.py" -v`
  - `python -m unittest discover -s tests -p "test_ollama_agent.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - live smoke: `python scripts\externals\openai_agent_api.py`, `python scripts\ctcp_support_bot.py --stdin --provider ollama_agent|api_agent|codex_agent`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 只改兜底文案，不修 provider 链。
  - 让 support bot 继续吞掉 deferred provider 状态并统一回“模型不可用”。
  - 继续让占位 `OPENAI_API_KEY=ollama` 覆盖 notes 凭证。
- user_visible_effect:
  - 真实需求消息不再因为 provider 串联失败直接掉到统一不可用兜底。
  - 本地 Ollama 与外部 API 都能产出 support reply artifact。
  - codex/manual_outbox disabled 时也能返回 customer-facing deferred reply。

## Plan

1. Docs/Spec:
   记录新的 queue item、CURRENT/LAST 摘要与 issue-memory。
2. Code:
   修 support provider 候选链与 deferred fallback；把 support reply 的 `ollama_agent` 改走原生 `/api/chat`；收紧 external API 凭证解析。
3. Verify:
   跑 targeted regressions、triplet guard、live smoke、canonical verify。
4. Report:
   回填验证证据、剩余风险和 demo 路径。

## Notes / Decisions

- Default choices made:
  - 优先最小修补 support reply provider 链，不扩大到 frontend 风格层。
- Alternatives considered:
  - 直接更换本地模型或强制改成外部 API-only；拒绝，因为当前主要断点是 provider wiring 与凭证解析。
- Any contract exception reference:
  - None.
- Issue memory decision:
  - add `ai_context/problem_registry.md` Example 6.
- Skill decision:
  - skillized: yes (`ctcp-workflow`, `ctcp-verify`)
