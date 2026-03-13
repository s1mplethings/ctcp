# Task Archive

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done`

## Active Task

- Queue Item: `ADHOC-20260313-support-api-first-local-degrade`
- Date: 2026-03-13
- Topic: support 回复锁到 api_agent，并把项目 zip/截图直发链路接到 Telegram
- Status: `blocked`

## Context

- Why this item now?
  用户继续要求“添加发项目截图和包发功能”。当前 support lane 已经能把客服回复锁到 `api_agent`，但 Telegram 入口只有 `sendMessage`，没有真实的 `sendDocument/sendPhoto` 执行链，因此 bot 只能在文本里承诺“可以打包发给你”，却无法基于真实项目产物直发。
- Dependency check:
  - `ADHOC-20260312-support-all-turns-model-routing`: `doing`
  - `ADHOC-20260312-support-api-encoding-hardening`: `done`
  - `ADHOC-20260312-support-project-state-grounding-hardening`: `done`
- Scope boundary:
  - 只调整 support reply 的 provider 默认、降级链、用户可见 failure wording 与对应 regression/doc evidence。
  - 不改 `scripts/ctcp_front_bridge.py`、`scripts/ctcp_dispatch.py`、`scripts/ctcp_orchestrate.py` 的执行状态机。
  - 不扩成 Telegram bot 全量重构、provider SDK 更换或前端 PM 文案大改。

## Task Truth Source

- task_purpose:
  让 `scripts/ctcp_support_bot.py` 在 Telegram 通道里能基于绑定 run 的真实产物直接发送项目 zip/截图，并把客服回复继续锁到 `api_agent`；当没有真实交付物时，要直接说没有，不能编造“稍后发邮箱”。
- allowed_behavior_change:
  - 可更新 `scripts/ctcp_support_bot.py` 的 default dispatch config、support provider candidate 顺序、reply failover 判定、local degrade notice、fallback doc。
  - 可更新 support greeting/smalltalk 的 retry guard，避免旧项目上下文污染或 preset 问候句落到用户侧。
  - 可新增 Telegram `sendDocument/sendPhoto`、public delivery artifact discovery、zip materialization 和用户可见 direct-send wiring。
  - 可更新 `docs/10_team_mode.md`、`docs/dispatch_config.support_bot.sample.json`、`agents/prompts/support_lead_reply.md` 以同步 support lane 契约。
  - 可更新 `tests/test_support_bot_humanization.py`、`tests/test_runtime_wiring_contract.py` 覆盖 API-first 与 local degrade 行为。
  - 可更新 `ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 及对应 archive 文件记录本轮证据。
- forbidden_goal_shift:
  - 不得把这次任务扩大成新的 bridge/orchestrator/dispatch 架构重写。
  - 不得通过新增另一套 preset 文案替代现有机械 fallback。
  - 不得让 support reply 继续 silently 掉到 `codex_agent`、`manual_outbox` 或本地模板来冒充正常客服回复。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `docs/dispatch_config.support_bot.sample.json`
  - `agents/prompts/support_lead_reply.md`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260313-support-api-first-local-degrade.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260313-support-api-first-local-degrade.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `frontend/conversation_mode_router.py`
  - `frontend/response_composer.py`
  - 与本次 support API-first 路由无关的其他未提交工作树改动
- completion_evidence:
  - 默认 support provider 变成 `api_agent`，greeting/smalltalk/project turn 的成功路径不再先走 `ollama_agent`。
  - `api_agent` 不可用、空回复、乱码或不可消费 reply 时，只会降级到本地 provider，并在用户可见回复里明确说明 API 当前不可用。
  - 旧的固定 `“暂时还没连上稳定的回复能力”` / `“收到，我先帮你整理一下”` shell，以及 `“你好，随时可以开始。你说说看要做什么？”` 这类 preset 问候句不再出现在 support runtime fallback。
  - 用户明确要 zip/截图且绑定 run 确实有真实项目产物时，Telegram 入口会直接发 `document/photo`；没有真实产物时，不再口头承诺发邮箱或稍后发送。
  - targeted regressions、triplet guard、workflow gate、canonical verify 留下 `connected + accumulated + consumed` 证据。

## Analysis / Find

- Entrypoint analysis:
  - 用户入口为 `scripts/ctcp_support_bot.py::process_message`。
- Downstream consumer analysis:
  - `process_message()` -> `support_provider_candidates()` -> `execute_provider(api_agent|ollama_agent)` -> `artifacts/support_reply.provider.json` -> `build_final_reply_doc()` -> `artifacts/support_reply.json`。
- Source of truth:
  - support session `dispatch_config.json`
  - support session `support_prompt_input.md`
  - support session `support_reply.provider.json`
  - support session `support_reply.json`
  - support session `support_session_state.json`
- Current break point / missing wiring:
  - 默认 support provider 仍偏 `ollama_agent`。
  - user-visible support reply fallback 仍混有 `manual_outbox` / fixed shell。
  - API failover 状态不会稳定传递到本地 degrade 回复中。
- Repo-local search sufficient: `yes`

## Integration Check

- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `scripts/ctcp_support_bot.py` plus support-lane contract docs/tests
- downstream:
  `support_provider_candidates()` -> `execute_provider()` -> `artifacts/support_reply.provider.json` -> `build_final_reply_doc()` -> `artifacts/support_reply.json`
- source_of_truth:
  support session `dispatch_config.json`, `support_prompt_input.md`, `support_reply.provider.json`, `support_reply.json`, `support_session_state.json`
- fallback:
  `api_agent` 失败时仅允许降级到本地 provider；若本地也失败，用户可见回复必须直接说明当前连不上
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - prompt-only wording patch without runtime provider changes
  - keeping manual_outbox/codex in the normal support-reply fallback chain
  - replacing one canned fallback shell with another canned shell
- user_visible_effect:
  - 正常客服回复默认来自 `api_agent`；API 不可用时，用户会直接知道当前连不上，并收到本地接手的自然回复或明确失败说明。

## Plan

1. Docs/Spec:
   绑定 queue/CURRENT/LAST/archive，并同步 support lane 文档与 sample config。
2. Code:
   收口 `scripts/ctcp_support_bot.py` 默认 provider、failover、final reply behavior，并接上 Telegram 附件发送。
3. Verify:
   跑 targeted regressions、triplet guard、workflow gate、canonical verify。
4. Report:
   回填验证证据、首个失败点和最小修复策略。

## Notes / Decisions

- Default choices made:
  - 把“本地降级”默认解释为本机可用的本地模型 provider，而不是 `manual_outbox` deferred shell。
- Alternatives considered:
  - 保留 `manual_outbox` 做用户可见 fallback；拒绝，因为这会继续产生预设式客服回复。
- Any contract exception reference:
  - None.
- Issue memory decision:
  - add one new user-visible failure entry to `ai_context/problem_registry.md`.
- Skill decision:
  - skillized: no, because this is a repository-local support routing correction, not a reusable workflow asset.

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `docs/dispatch_config.support_bot.sample.json`
  - `agents/prompts/support_lead_reply.md`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260313-support-api-first-local-degrade.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260313-support-api-first-local-degrade.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => first run `1`
  - minimal fix strategy: treat mojibake as unusable API reply and align old fallback-text regressions to the new API-first/no-canned-fallback contract
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => second run `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => second run `0` (23 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (15 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure point: `patch check (scope from PLAN)`
    - failure detail: `generated_projects/vn_story_organizer/README.md` is still reported out-of-scope by `scripts/patch_check.py` under the repo-wide current PLAN gate
    - minimal fix strategy: bind an explicit contract/scope update for `generated_projects/vn_story_organizer/` or move delivery outputs out of the repo worktree before rerunning canonical verify
