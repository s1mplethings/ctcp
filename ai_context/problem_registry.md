# Problem Registry (Reusable Template + Examples)

Purpose:
- Capture recurring failure patterns as reusable institutional memory.
- Keep entries short, reproducible, and directly actionable.

When to add:
- Same class of failure appears >= 2 times.
- A failure required non-obvious debugging steps.
- A policy mismatch caused avoidable rework.

## Entry Template

- Symptom:
- Repro:
- Root cause:
- Fix:
- Prevention:
- Tags:

## Example 1

- Symptom:
  Agent/patch claims "verified" but no reproducible evidence artifacts exist.
- Repro:
  Run build/test manually without saving structured logs; output cannot be audited later.
- Root cause:
  Verification flow was fragmented and not tied to a hard gate entrypoint.
- Fix:
  Standardize on `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`; record command and result in `meta/reports/LAST.md`.
- Prevention:
  Treat missing verify evidence as FAIL in review.
- Tags:
  verify, gate, evidence, reproducibility

## Example 2

- Symptom:
  Docs claim rules that scripts do not enforce (contract drift).
- Repro:
  Compare `docs/03_quality_gates.md` against `scripts/verify_repo.*`; documented gate differs from actual executed gate list.
- Root cause:
  Documentation changed independently from gate scripts.
- Fix:
  Update docs to script-aligned behavior or implement missing gate in scripts in the same patch.
- Prevention:
  Every gate change must include paired doc update and a verify run record.
- Tags:
  docs, contract, drift, verify

## Example 3

- Symptom:
  Customer-visible support replies suddenly expose internal file names, agent labels, or system fallback wording such as `verify_report.json`, `failure bundle`, or `internal agent`.
- Repro:
  Trigger provider/model fallback branches in `scripts/ctcp_support_bot.py`, or emit a raw reply containing `TRACE/logs/outbox/diff --git` and let it reach the public reply path.
- Root cause:
  The public reply path over-trusts raw provider text, so internal markers leak before the customer-facing normalization gate rewrites them.
- Fix:
  Route every customer-visible notice through `build_final_reply_doc()`, keep `support_reply.json.reply_text` as the single visible artifact, and add regressions for forbidden-token fallback branches.
- Prevention:
  Treat any direct public notice containing internal labels/raw exceptions as a contract violation; cover new fallback branches with support-bot humanization tests before merge.
- Tags:
  support, frontend, leakage, wording, fallback

## Example 4

- Symptom:
  Telegram bot greeting works, but the first real project turn immediately fails with external API 401 and tells the user the model call is unavailable.
- Repro:
  Start the Telegram bot with `OPENAI_API_KEY=ollama` and no `OPENAI_BASE_URL`, then send a real project goal that creates a new run.
- Root cause:
  Greeting/smalltalk uses a local reply path, but new-run dispatch still defaults to `api_agent`; meanwhile `api_agent` treated any non-empty key as ready, so the placeholder `ollama` value slipped through until real execution hit OpenAI and failed.
- Fix:
  Align Telegram-created run dispatch configs away from `api_agent` when external API env is not truly ready, and treat `OPENAI_API_KEY=ollama` without `OPENAI_BASE_URL` as invalid for external API mode.
- Prevention:
  Validate provider readiness at run-creation time, not only after dispatch starts; add regression coverage for local greeting plus project-intake transition.
- Tags:
  telegram, provider, api, config, 401, local-first

## Example 5

- Symptom:
  Support-bot project turns regress to generic kickoff wording or leak `missing runtime_target`-style internal markers instead of reflecting the current detailed requirement.
- Repro:
  1. Start a support session and send a detailed requirement such as `输入是单目视频，先离线处理，输出PLY`.
  2. Let the provider return a low-signal raw reply like `收到，继续推进。missing runtime_target`.
- Root cause:
  The support reply pipeline over-trusted low-signal raw provider text; the frontend-reviewed customer reply was bypassed even when the latest user requirement was richer and the raw text still carried internal markers.
- Affected entrypoint:
  Support session path (`scripts/ctcp_support_bot.py::process_message` -> `build_final_reply_doc`).
- Affected modules:
  `scripts/ctcp_support_bot.py`, `frontend/response_composer.py`
- Observed fallback behavior:
  The user sees `missing runtime_target`-style internal markers or a low-signal echo instead of a frontend-reviewed customer summary.
- Expected correct behavior:
  Detailed support turns should prefer the latest detailed requirement source and suppress internal markers before the reply becomes public.
- Fix:
  Stop preserving low-signal/internal-marker raw support replies in `scripts/ctcp_support_bot.py` and keep the frontend-reviewed reply authoritative for project-like turns.
- Fix attempt status:
  2026-03-11 scoped cleanup bound under `ADHOC-20260311-remove-legacy-telegram-bot`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_frontend_rendering_boundary.py`.
- Prevention:
  Treat low-signal support replies as fallback candidates, not authoritative agent text; keep a direct frontend regression for internal-marker suppression in project-like support turns.
- Tags:
  support, frontend, reply-shaping, requirement-source, leakage

## Example 6

- Symptom:
  Support bot `/start` 正常，但第一条真实需求消息会连续打穿 `ollama_agent`、`api_agent`、`codex_agent`，最后只回“暂时还没连上稳定的回复能力”。
- Repro:
  1. 启动 `scripts/ctcp_support_bot.py`，让 support session `dispatch_config.json` 处于 `mode=manual_outbox`、`support_lead=ollama_agent`。
  2. 让本地 Ollama 模型走 OpenAI-compatible `/v1/chat/completions`，同时进程环境存在占位值 `OPENAI_API_KEY=ollama` 且没有显式 `OPENAI_BASE_URL`。
- Root cause:
  Support provider 候选链没有真正把 `manual_outbox` 当成回复兜底；`process_message()` 只把 `executed` 当成功，忽略了 `outbox_created` 这类 deferred 状态；`ollama_agent` 复用了 OpenAI-compatible path 而不是 Ollama 原生 `/api/chat`；外部 `api_agent` 又被进程环境里的占位 key 抢先覆盖了本机私有 notes 中的真实凭证。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `tools/providers/ollama_agent.py`, `tools/providers/api_agent.py`, `scripts/externals/openai_responses_client.py`
- Observed fallback behavior:
  用户看到统一的“回复能力没连上”兜底文案，而不是继续走 customer-facing deferred reply 或实际可用 provider。
- Expected correct behavior:
  `ollama_agent` 应该能通过 Ollama 原生 chat 接口返回 support reply；`api_agent` 应该在占位 env key 存在时仍能回退到真实 notes 凭证；所有 provider 都失败时应退回 `manual_outbox` 并保持 customer-facing 回复。
- Fix:
  把 `manual_outbox` 接入 support provider 候选链并接受 deferred 状态，给 support reply 的 `ollama_agent` 改走原生 `/api/chat`，并让 external API 凭证解析忽略会遮蔽 notes 凭证的占位 `OPENAI_API_KEY=ollama`。
- Fix attempt status:
  2026-03-12 scoped fix bound under `ADHOC-20260312-support-provider-connectivity-repair`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py`, `tests/test_ollama_agent.py`, `tests/test_api_agent_templates.py`, and `tests/test_openai_responses_client_resilience.py`.
- Prevention:
  把 deferred provider 路径视为一等回复路径而不是失败；local/notes/env 三层 provider 凭证解析必须显式防止 placeholder 值遮蔽真实配置；对本地 Ollama 的 support reply 不要再绕过原生 `/api/chat`。
- Tags:
  support, provider, fallback, ollama, api, credentials

## Example 7

- Symptom:
  support bot 已能给出自然客服回复，但项目型消息并没有真正进入后台制作流程；客服侧看不到生产 run 的 whiteboard / librarian 上下文，用户也只会得到 support-only 的泛化答复。
- Repro:
  1. 通过 `scripts/ctcp_support_bot.py` 发送一条明确项目需求，例如“我想做一个帮我整理剧情结构的项目”。
  2. 检查 support session artifacts 与 production run artifacts，发现 support turn 只写 `support_inbox.jsonl` / `support_reply.json`，没有通过 `scripts/ctcp_front_bridge.py` 创建或绑定 run，也没有消费 `${run_dir}/artifacts/support_whiteboard.json`。
- Root cause:
  support bot 的入口 `process_message()` 只把消息交给 reply provider，并未走 frontend-to-execution bridge；共享 whiteboard 与 librarian 线索只在 `scripts/ctcp_dispatch.py::dispatch_once()` 的生产 run 路径内可见，导致 support entrypoint 与 backend flow 脱节。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, `scripts/ctcp_dispatch.py`
- Observed fallback behavior:
  用户看到的是自然但偏泛的客服答复；后台真实 run、whiteboard、librarian 检索线索都没有成为 support reply 的可见依据。
- Expected correct behavior:
  support bot 的项目型 turn 应通过 `ctcp_front_bridge` 创建/绑定/推进 run，并通过 bridge-safe helper 记录 support turn 到共享 whiteboard、读取 librarian hits 与真实 run status，再由 customer-facing reply 消费这些真实状态。
- Fix:
  给 `scripts/ctcp_front_bridge.py` 增加 support entry 所需的 context/mutation helper，并让 `scripts/ctcp_support_bot.py` 在项目型 turn 上通过 bridge 绑定 run、记录 support turn、读取 status/whiteboard context，再把这些上下文注入 support prompt 与 customer-facing render 流。
- Fix attempt status:
  2026-03-12 scoped fix bound under `ADHOC-20260312-support-bot-backend-bridge-wiring`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  任何声称“客服已接上后台流”的能力，都必须提供 support entrypoint -> bridge -> run artifact -> whiteboard/librarian consumption 的可执行路径与回归证明；只改 prompt/文案不算完成 wiring。
- Tags:
  support, bridge, whiteboard, librarian, runtime-wiring

## Example 8

- Symptom:
  support bot 在同一会话里会突然“忘记项目是什么”，并把 `没有，你先做着` 之类的短句理解成“先暂停项目”；首句问候还可能漂成英文。
- Repro:
  1. 先发送一条明确项目需求，例如 `i want to create a project to help me structure narrative projects, especially in clarify storyline`。
  2. 再发送短句 follow-up，例如 `没有，你先做着`。
  3. 当显式 provider 为 `api_agent` 且 reply 中带有 Unicode replacement char 时，观察 support bot 路由跌到 `ollama_agent` 并返回错误语义。
- Root cause:
  `scripts/ctcp_support_bot.py` 早期把 persistent project brief 和 latest turn 混在单一 `task_summary` 槽里；conversation routing 又直接吃整段 history，导致短句 follow-up 被历史高信号拖成新的 `PROJECT_INTAKE`；同时显式 `api_agent` override 仍会串进全 provider 候选链，reply shaping 一旦判定 mojibake 就跌回本地模型。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  greeting 走 provider 后漂语言；项目 brief 被低信息 turn 覆盖；API reply 被拒后落入 `ollama_agent`，产生“先暂停/暂时不做”的错误回复。
- Expected correct behavior:
  persistent project brief、turn memory、provider runtime buffer 应隔离存储；问候应保持 `GREETING/SMALLTALK` 模式边界，但正常用户可见回复仍应走 configured support model；显式 API route 失败时只能 customer-facing degrade 或 manual fallback，不能跨到另一语义 provider。
- Fix:
  拆 support session state schema，按 project_memory / turn_memory / provider_runtime_buffer 隔离；conversation mode 改成 current-turn-first；显式 provider override 走 strict route，provider reply 有 replacement char 时先清洗再决定是否降级；若产品要求全部用户可见回复走模型，则 greeting/smalltalk 也应经 support model，而不是本地模板。
- Fix attempt status:
  2026-03-12 scoped fix bound under `ADHOC-20260312-support-memory-isolation-and-api-route-lock`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  support session state 里任何 persistent project memory 都不能被短句 follow-up 直接覆盖；显式 provider override 的 fallback 语义必须在测试里锁定，不允许跨 provider semantic drift；greeting/smalltalk 是否本地回复必须由当前 authoritative support contract 明确规定，不能在 docs 与 runtime 中漂移。
- Tags:
  support, memory, routing, api, fallback, mojibake

## Example 9

- Symptom:
  用户明确要求“所有用户可见回复都走模型”，但 support bot 的 greeting/smalltalk 仍由本地固定话术 fast path 抢答，导致第一条回复与后续项目轮不是同一个 model-authored support voice。
- Repro:
  1. 启动 `scripts/ctcp_support_bot.py --provider api_agent telegram`。
  2. 发送 `你好`。
  3. 观察 `support_reply.json.provider` 或用户实际回复，发现命中本地 `local_smalltalk` 而不是 `api_agent`。
- Root cause:
  先前为了解决语言漂移而在 `scripts/ctcp_support_bot.py` 里加了 greeting local fast path，但 authoritative docs/prompt/runtime 没有随产品口径继续同步，导致“全部走模型”的要求与实际执行不一致。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `docs/00_CORE.md`, `docs/10_team_mode.md`, `agents/prompts/support_lead_reply.md`, `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  greeting/smalltalk 不进 provider 链，用户第一条回复固定成模板化本地话术。
- Expected correct behavior:
  `GREETING/SMALLTALK` 仍不进入项目规划逻辑，但正常用户可见回复应由 configured support model 生成，只有 provider failure/deferred 时才允许模型外降级。
- Fix:
  删掉 normal-path `local_smalltalk` 分支，并同步 foundational docs/prompt contract，明确“mode gate != local reply bypass”。
- Fix attempt status:
  2026-03-12 scoped fix bound under `ADHOC-20260312-support-all-turns-model-routing`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  support lane 的“是否走模型”必须由 authoritative docs 和 runtime 同步约束；任何 user-visible fast path 都需要显式产品确认与回归锁定。
- Tags:
  support, product-policy, routing, greeting, model

## Example 10

- Symptom:
  support bot 明明走的是 `api_agent`，但 Telegram 用户看到的中文回复变成 `ãܸ˰...` / `���...` 这类乱码。
- Repro:
  1. 让 `scripts/ctcp_support_bot.py --provider api_agent telegram` 处理一条中文消息，例如 `你好`。
  2. 同时对比 `openai_responses_client.call_openai_responses()` 的直连结果、support session 的 `logs/agent.stdout` 和 `artifacts/support_reply.provider.json`。
- Root cause:
  HTTP 层返回的中文是正常的，但 `tools/providers/api_agent.py` 通过子进程调用 `scripts/externals/openai_agent_api.py` 时，child stdout 在 Windows 下可能按本地 codepage 发字节；父进程却固定按 UTF-8 解码，导致 provider 产物先变成 mojibake，再进入用户可见回复。support bot 原先的乱码抑制也主要盯 `\ufffd`，对没有 replacement char 的 mojibake 覆盖不够。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `tools/providers/api_agent.py`, `scripts/externals/openai_agent_api.py`, `scripts/externals/openai_plan_api.py`, `scripts/externals/openai_patch_api.py`, `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  用户直接收到乱码中文，而不是正常中文或 customer-facing degrade reply。
- Expected correct behavior:
  provider 子进程和 wrapper 默认使用 UTF-8；若外部命令仍输出本地 codepage，父进程应能恢复正确中文；任何残余 mojibake 都不应直达用户。
- Fix:
  把 `api_agent` 改为字节级捕获并带本地 codepage fallback 解码，默认对子进程设置 UTF-8 环境；OpenAI wrapper 显式 reconfigure stdio 为 UTF-8；support bot 扩大 mojibake 检测，抑制没有 `\ufffd` 的乱码直出。
- Fix attempt status:
  2026-03-12 scoped fix bound under `ADHOC-20260312-support-api-encoding-hardening`.
- Regression test status:
  Covered by `tests/test_api_agent_templates.py` and `tests/test_support_bot_humanization.py`.
- Prevention:
  对任何经子进程调用的 provider 路径，都不要假设 child stdout 一定是 UTF-8；中文用户可见回复必须有 live regression，至少覆盖“直连正常、provider stdout 异常”的链路。
- Tags:
  support, encoding, mojibake, api_agent, windows, subprocess

## Example 11

- Symptom:
  support bot 在同一个项目会话里先说“会开始做第一版”，但实际 backend 没有开始制作；同时项目目标还会被后续的技术约束消息覆盖。
- Repro:
  1. 在已绑定 run 的 support session 里先发送真实项目目标，例如“我想做一个帮我理顺剧情结构的项目”。
  2. 再发送实现细节，例如 `window开发，然后ui可以使用qt6`。
  3. 接着发送执行指令，例如 `你先做出第一版给我看，然后我在做调整`。
- Root cause:
  `scripts/ctcp_support_bot.py` 的 `should_refresh_project_brief()` 之前对长文本过于宽松，导致实现细节覆盖长期项目目标；`frontend/conversation_mode_router.py` 又只在“有效 task summary”存在时才稳定保留项目 follow-up，于是 bound run 下的执行指令可能掉成 `SMALLTALK`；即便 backend 已 `blocked`，`frontend/response_composer.py` 仍可能直接保留 raw provider 的 optimistic “开始做第一版” 文本。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `frontend/conversation_mode_router.py`, `frontend/response_composer.py`
- Observed fallback behavior:
  长期项目目标被平台/框架偏好覆盖；执行指令没有真正进入 backend bridge；用户看到的却是“已经开始做第一版”式承诺。
- Expected correct behavior:
  长期项目目标、技术约束、执行指令必须隔离存储；只要 session 已绑定 run，`先出第一版` 这类执行指令就应继续走项目路由；blocked / waiting backend 状态只能输出 grounded customer-facing reply，不能保留 optimistic raw promise。
- Fix:
  在 support session state 中新增独立的技术约束和执行指令记忆区；收紧 `project_brief` refresh 条件；在 conversation router 中增加 active-run execution-followup 路由；在 reply composer 中强制 blocked / waiting 状态改用 state-grounded reply。
- Fix attempt status:
  2026-03-12 scoped fix bound under `ADHOC-20260312-support-project-state-grounding-hardening`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  support 的长期项目记忆不能再用“长度够长”作为刷新条件；bound-run follow-up 必须由 runtime binding 参与路由，而不是只依赖当前摘要文本；任何 blocked / waiting backend 状态都必须由 frontend reply layer 兜底重写，禁止 raw promise 直出。
- Tags:
  support, memory, routing, blocked-state, overpromise, frontend

## Example 12

- Symptom:
  用户明确要求“客服所有正常回复都来自 `api_agent`，连不上就直接说连不上并降级到本地”，但 support bot 仍默认先走 `ollama_agent`，或者在 API 失败后掉到固定 `暂时还没连上稳定的回复能力` / `收到，我先帮你整理一下` 话术。
- Repro:
  1. 让 `scripts/ctcp_support_bot.py` 使用默认 support session `dispatch_config.json`。
  2. 发送任意 greeting 或项目型消息。
  3. 再让 `api_agent` 返回 connect timeout / disabled / invalid json / garbled reply。
  4. 观察 `support_reply.json`，发现要么正常路径不是 `api_agent`，要么用户看见固定机械 fallback shell，而不是明确的 API-unavailable + local-fallback reply。
- Root cause:
  `default_support_dispatch_config()` 之前把 `support_lead` 默认到 `ollama_agent`；`support_provider_candidates()` 还允许 `manual_outbox` / `codex_agent` 混进用户可见 support reply 候选链；`model_unavailable_reply_doc()` 和 `deferred_support_reply_doc()` 则继续输出固定 fallback shell，导致产品要求和 runtime 行为漂移。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`, `docs/dispatch_config.support_bot.sample.json`, `agents/prompts/support_lead_reply.md`
- Observed fallback behavior:
  正常 turn 不是先走 `api_agent`；API 失败时用户看见模板化“没连上稳定回复能力”/“我先帮你整理一下”，却不知道当前已经切到本地或本地也不可用。
- Expected correct behavior:
  默认 customer-facing support reply 应先走 `api_agent`；API 不可用或 reply 不可用时，只允许降级到本地 provider，并在用户可见回复中直接说明 API reply path 当前不可用；若本地也失败，应直接说当前 API/本地都没接上，不再伪装成正常处理中。
- Fix:
  把 support 默认 provider 改成 `api_agent`，把用户可见 support reply 候选链收口到 `api_agent -> local provider`，把 API failover 状态显式注入本地 reply/final reply，并移除旧固定 fallback shell。
- Fix attempt status:
  2026-03-13 scoped fix bound under `ADHOC-20260313-support-api-first-local-degrade`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  support lane 的默认 provider、local degrade 语义和用户可见 fallback wording 必须由 docs/prompt/runtime 同步锁定；任何 user-visible failover 改动都需要回归覆盖“API 成功、API 失败转本地、API+本地都失败”三条路径。
- Tags:
  support, api-first, fallback, local-degrade, product-policy, wording

## Example 13

- Symptom:
  客服对外说“项目已经完成，可以打包发你”，但实际发出的项目目录只有 `main.py + README.md` 这类薄壳占位实现，不是用户要求的 CTCP-style 多文档项目结构。
- Repro:
  1. 在已绑定 run 的 support session 里让 bound run 触碰 `generated_projects/<slug>/main.py` 这类占位目录。
  2. 用户追问“做成什么样子，能不能打包发我”。
  3. support delivery runtime 直接把 placeholder 目录打成 zip，客服回复却按“完整项目已完成”描述。
- Root cause:
  support 的 public delivery 之前只做“发现目录 -> 直接 zip”，不会判断目录是不是完整 CTCP-style 项目；prompt context 也不知道这次可发包到底是 scaffold 还是单文件占位目录，导致 customer-facing 描述与真实交付物脱节。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message` and `scripts/ctcp_support_bot.py::emit_public_delivery`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`, `agents/prompts/support_lead_reply.md`
- Observed fallback behavior:
  用户收到的是单文件占位 zip，但客服话术像是在交付完整项目；继续围绕 repo 内 `generated_projects/` 交付还会撞上 current PLAN 的 `Scope-Deny`。
- Expected correct behavior:
  如果当前项目目录只是薄壳，占位目录不能直接当 customer package；support runtime 应先在 repo 外 materialize 一份 CTCP-style scaffold 再发送，且客服必须按 scaffold 如实描述，不得把它说成 feature-complete implementation。
- Fix:
  在 support delivery runtime 中识别 placeholder project dir，改为外部 materialize `scaffold --source-mode live-reference` 的 CTCP-style package，并把真实 package shape 注入 support prompt/context。
- Fix attempt status:
  2026-03-13 scoped fix bound under `ADHOC-20260313-support-ctcp-scaffold-package`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py`, `tests/test_runtime_wiring_contract.py`, and `tests/test_scaffold_reference_project.py`.
- Prevention:
  customer-visible package description必须绑定真实 delivery shape；任何“项目可打包发送”的 support 能力都要区分 placeholder/source-dir/scaffold 三种形态，并对 placeholder->scaffold materialization 加回归。
- Tags:
  support, delivery, scaffold, overpromise, placeholder, package

## Example 14

- Symptom:
  用户已经多次要求“不要像接待台话术”，但 task turn 仍会以 `收到 / 我先帮你整理一下 / 为了更好地帮助您` 这类开场开头，并在有当前任务状态时重复追问或重述目标。
- Repro:
  1. 绑定一个已有 `CURRENT.md` / run 状态的项目任务。
  2. 发送进度追问、失败追问或结果交付追问。
  3. 观察用户可见回复，发现首句没有直接进入任务本体，或者虽然礼貌但没有给出明确下一步。
- Root cause:
  仓库长期只有“自然一点 / 不要机械”这类软口径，没有把 task turn 的状态绑定字段、禁用句式、阶段规则和 lint 验收定义成单一权威合同，导致实现更容易优化成安全礼貌壳而不是任务推进。
- Affected entrypoint:
  support/frontend user-visible task reply path
- Affected modules:
  `docs/10_team_mode.md`, `docs/11_task_progress_dialogue.md`, `frontend/response_composer.py`, `agents/prompts/support_lead_reply.md`
- Observed fallback behavior:
  回复听起来礼貌，但任务没有前进；用户需要反复重申目标或催问下一步。
- Expected correct behavior:
  首句直接进入任务本体，先给判断再给动作，除非真的阻塞否则不反问，并且每条消息都推进一个具体下一步。
- Fix:
  增加单一权威的任务推进型对话合同，要求 reply 在发出前绑定 `task_goal/current_phase/last_confirmed/blocker/message_purpose/question_needed/next_action`，并定义 response lint。
- Fix attempt status:
  2026-03-14 contract-first docs refactor bound under `ADHOC-20260314-dialogue-showcase-metadata-contracts`.
- Regression test status:
  Pending dedicated response-lint automation; contract acceptance is now defined in `docs/11_task_progress_dialogue.md` and `docs/03_quality_gates.md`.
- Prevention:
  任何 user-visible task dialogue 改动都必须同步更新任务推进型合同与对应 lint/回放验证，不能只改 prompt 或报告措辞。
- Tags:
  support, frontend, dialogue, wording, task-progress, lint

## Example 15

- Symptom:
  run 报告、generated/scaffold 项目来源信息和人类可读总结之间的版本号或 provenance 口径不一致，用户难以判断当前交付到底来自哪个仓库版本。
- Repro:
  1. 对比 root `VERSION`、run 报告、`meta/reference_source.json`、scaffold report、人工总结。
  2. 观察其中有的只写 `source_commit`，有的只写自然语言版本描述，有的完全缺少版本字段。
- Root cause:
  仓库已有 commit provenance，但没有把 repo version authority、run report version copy、generated project `source_version` 和 mismatch fail/warn 规则收口成单一合同。
- Affected entrypoint:
  run report generation, scaffold/live-reference export, user-visible delivery summary
- Affected modules:
  `VERSION`, `docs/30_artifact_contracts.md`, `docs/40_reference_project.md`, `meta/reports/LAST.md`
- Observed fallback behavior:
  用户看到了交付物和报告，但无法快速确定它们是不是同一版本来源。
- Expected correct behavior:
  所有 version claim 都从 root `VERSION` 派生，所有 provenance-bearing artifacts 同时携带 `source_version + source_commit`，且 mismatch 有明确失败/警告语义。
- Fix:
  在 artifact/reference/quality-gate 文档中把 `VERSION` 定义为单一真源，并要求 generated/scaffold/run/showcase 文档统一携带 `source_version`。
- Fix attempt status:
  2026-03-14 contract-first docs refactor bound under `ADHOC-20260314-dialogue-showcase-metadata-contracts`.
- Regression test status:
  Pending dedicated metadata-consistency automation; contract acceptance is now defined in `docs/03_quality_gates.md`, `docs/30_artifact_contracts.md`, and `docs/40_reference_project.md`.
- Prevention:
  任何 run/report/scaffold provenance 变更都必须同步更新 version truth contract，并把 mismatch 处理写进 gate acceptance，而不是留给人工解释。
- Tags:
  metadata, version, provenance, scaffold, report, consistency

## Example 16

- Symptom:
  风格问题看起来“修好了”，但一换到新对话、新语言或长上下文后，production assistant 又退回机械式客服腔；同时 style test transcript 和正式 support session 混在一起，导致结果不干净也不可回归。
- Repro:
  1. 在同一个 support 会话里反复告诉系统“不要像接待台那样说话”。
  2. 观察当前会话内回复似乎变自然。
  3. 重新开一个新对话、切换到中英混合表达、或者拉长上下文后再测，发现系统又开始用 greeting/apology/filler 开场。
- Root cause:
  仓库只有 production conversation path，没有独立的 Persona Test Lab；production persona、test user persona、judge/scoring 没有分层，导致测试和正式会话共享上下文，无法做 fresh-session style regression。
- Affected entrypoint:
  support/frontend-visible task reply path and future style-regression runner
- Affected modules:
  `docs/11_task_progress_dialogue.md`, `docs/14_persona_test_lab.md`, `persona_lab/`, `docs/10_team_mode.md`, `docs/30_artifact_contracts.md`
- Observed fallback behavior:
  用户在正式会话里不断纠正风格，但系统只是在该会话暂时学会绕开禁用句式；换个上下文又恢复模板腔，而且没有 transcript/score/fail reasons 可供回归。
- Expected correct behavior:
  production assistant、test user persona、judge/scoring 三层分离；每个 case 用 fresh session；结果必须带 transcript、score、fail reasons，并且多语言与长对话漂移都可重放。
- Fix:
  先增加独立的 Persona Test Lab 合同和静态资产，再补一个 fixture runner / judge 基线，要求 fresh-session-per-case、固定 persona、评分 rubric、最小回归 cases，以及 repo 外的结果产物结构。
- Fix attempt status:
  2026-03-14 docs-first contract landing bound under `ADHOC-20260314-persona-test-lab-contracts`; 2026-03-15 fixture runner / judge baseline bound under `ADHOC-20260315-persona-test-lab-runner-judge`.
- Regression test status:
  Baseline runner/judge now exists in `scripts/ctcp_persona_lab.py` with `tests/test_persona_lab_runner.py`; live production-adapter regression is still pending.
- Prevention:
  任何“风格已修复”的声明都必须附带 isolated persona-lab evidence，而不是只引用同一正式会话里的主观观感。
- Tags:
  support, dialogue, persona-lab, context-isolation, regression, scoring

## Example 17

- Symptom:
  `python simlab/run.py --suite lite` 长期卡在 `S15_lite_fail_produces_bundle` / `S16_lite_fixer_loop_pass`，而且失败形态会来回漂移：有时 fixer prompt 丢 `failure_bundle.zip`，有时 second-pass reapply 被 managed dirty pointer 拦住，有时又变成 fixture patch 提前 patch-first fail 或坏 patch 意外直接 PASS。
- Repro:
  1. 运行 `python simlab/run.py --suite lite`。
  2. 查看 `S15` / `S16` 的 `TRACE.md`、`events.jsonl`、`artifacts/verify_report.json`、`logs/patch_apply.stderr.log`。
  3. 如果 `S15` 缺 `VERIFY_STARTED`、`S16` 第二次 `advance` 因 `PATCH_GIT_CHECK_FAIL` / `workflow_checks` 卡住，或者坏 patch 直接 `PASS: verify succeeded`，通常就是这类回归。
- Root cause:
  这是一个叠层回归。runtime 侧先后出现过 fixer dispatch 对 patch 路径丢 `failure_bundle.zip` 输入，以及 `LAST_BUNDLE.txt` 这类受管 run pointer 让 second-pass reapply 误判 dirty；在这些 runtime 缺口修掉后，SimLab fixture patch 仍依赖旧 README 头部、旧失败触发器和“环境里刚好还有别的 meta 脏改动”这种偶然条件，导致当前 `doc-only` profile 下的真实 first-failure 与场景预期脱钩。
- Fix:
  在 `scripts/ctcp_dispatch.py` 为 fixer patch 路径保留 `failure_bundle.zip` 输入，在 `scripts/ctcp_orchestrate.py` 只豁免受管 run pointer 的 dirty 检查；同时把 `tests/fixtures/patches/lite_fail_bad_readme_link.patch` / `lite_fix_remove_bad_readme_link.patch` 刷新成对当前 README + `CURRENT/LAST` 可 `git apply --check` 的最小 patch，并把坏 patch 的失败触发器切到当前 lite/doc-only profile 稳定执行的 `doc index check`。
- Prevention:
  每次改 README 顶部结构、verify profile、workflow gate 或 SimLab fixture，都先跑一次 `git apply --check` 覆核这两份 patch，再跑 `python simlab/run.py --suite lite`；不要让 SimLab fixture 依赖 incidental dirty meta state。
- Tags:
  simlab, fixtures, fixer-loop, verify-profile, doc-index, dirty-pointer

## Example 18

- Symptom:
  support 对话明明已经先做了场景分流，但“你是谁 / 你能做什么 / 怎么用”这类能力询问仍被折叠成 generic smalltalk，状态追问和项目开场也容易共用同一套 kickoff 壳。
- Repro:
  1. 调用 `frontend.conversation_mode_router.route_conversation_mode()` 处理 `你是谁` 或 `你能不能按 CTCP 的方式改前端这块`。
  2. 再用 `frontend.response_composer.render_frontend_output()` 渲染这些 turn。
  3. 观察 capability turn 落到 `SMALLTALK`，或者状态 fallback 用 `OK，这就开始` 这类 generic kickoff。
- Root cause:
  shared router 之前只区分 `GREETING/SMALLTALK/PROJECT_*/STATUS_QUERY`，没有把 capability query 作为独立场景；reply composer 的 fallback 也没有为身份/能力/使用方式问题提供独立 customer-facing reply。
- Affected entrypoint:
  support/frontend user-visible reply path
- Affected modules:
  `frontend/conversation_mode_router.py`, `frontend/response_composer.py`, `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  能力询问得到 generic smalltalk；状态追问和项目开场都可能复用偏泛的 kickoff 句壳。
- Expected correct behavior:
  support lane 应先把 capability query 从 generic smalltalk 中分离，再根据 greeting/capability/project/status 不同场景输出不同的 customer-facing entry reply。
- Fix:
  在 shared router 增加 `CAPABILITY_QUERY` 场景，给 response composer 增加 identity/usage/frontend-capability fallback reply，并让 support bot 的 latest-turn-only / stale-context guard 同步覆盖 capability turn。
- Fix attempt status:
  2026-03-16 scoped fix bound under `ADHOC-20260316-support-conversation-situation-routing`.
- Regression test status:
  Covered by `tests/test_frontend_rendering_boundary.py`, `tests/test_runtime_wiring_contract.py`, and `tests/test_support_bot_humanization.py`.
- Prevention:
  任何新增的 support 场景都要同时更新 shared router、customer-facing fallback reply、support bot non-project guard 和 focused regressions；不要只在 prompt 里口头说“先识别场景”。
- Tags:
  support, frontend, routing, capability-query, status-reply, dialogue

## Example 19

- Symptom:
  真实 Telegram 旧会话里只发一句 `你好`，support bot 仍会回“之前的剧情项目已经打包好了”并直接附带 zip 发送动作。
- Repro:
  1. 使用一个已经绑定旧 run 且 `package_ready=true` 的 support session。
  2. 在 Telegram 里只发送 greeting，例如 `你好`。
  3. 观察 `support_reply.json`，发现 reply_text 引用旧项目/旧交付，`actions` 里还带 `send_project_package(zip)`。
- Root cause:
  `scripts/ctcp_support_bot.py` 之前即使在 `GREETING / SMALLTALK / CAPABILITY_QUERY` turn，也会继续把旧 `project_brief`、`bound_run_id`、`public_delivery` 注入 prompt；最终 reply 阶段也不会剥离 provider 主动给出的 delivery action。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message` live Telegram path
- Affected modules:
  `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  简单寒暄被旧项目和旧 zip 交付状态污染，用户看见的像是在继续上一次交付。
- Expected correct behavior:
  non-project turn 默认只看 latest turn；除非最新 user turn 明确要求继续旧项目或直接请求 package/screenshot，否则 prompt 和 final actions 都不应携带旧交付上下文。
- Fix:
  对 non-project turn 关闭旧项目/旧交付 prompt 注入，并在 final reply 里剥离未被本轮显式请求的 `send_project_package` / `send_project_screenshot` action。
- Fix attempt status:
  2026-03-16 scoped fix bound under `ADHOC-20260316-support-greeting-stale-context-hardening`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  任何 support 的旧会话恢复逻辑都要区分“继续项目”与“只是寒暄”；非项目 turn 的 prompt/action gating 必须由 runtime 兜底，不要把防泄露责任只交给模型。
- Tags:
  support, telegram, stale-context, delivery-action, greeting, runtime

## Example 20

- Symptom:
  用户在真实 Telegram 里追问 `现在做到什么程度了`，support bot 只回 `这边已经进入处理阶段。` / `现在就在往下做。`，没有告诉用户已经做了什么、卡在哪里、接下来干什么。
- Repro:
  1. 让 support session 绑定一个已经有真实 run status 和 whiteboard tail 的项目 run。
  2. 发送 status/progress follow-up，例如 `现在做到什么程度了` 或 `就按之前的大纲继续走`。
  3. 观察 `support_reply.json.reply_text`，发现它只消费 `visible_state=EXECUTING` 的模板壳，而没有消费 run gate/status 与 whiteboard 里的已完成步骤。
- Root cause:
  `scripts/ctcp_support_bot.py` 先前只把状态压成 `stage/run_status/decision_count` 之类的粗粒度 backend state；`frontend/response_composer.py` 遇到 `STATUS_QUERY` 或 internal blocked project turn 时又直接落回 `compose_user_reply(EXECUTING)`，导致真实的 `review_cost executed / review_contract blocked / next repair` 这些信息没有进入用户可见回复。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::build_final_reply_doc` live Telegram progress path
- Affected modules:
  `scripts/ctcp_support_bot.py`, `frontend/response_composer.py`
- Observed fallback behavior:
  用户只看到泛化的“处理中”壳话术，不知道后台具体已经做了什么，也不知道当前阻塞和下一步。
- Expected correct behavior:
  status/progress reply 应自动总结已完成事项、当前阶段、当前阻塞或无阻塞状态、以及下一步动作；status-like follow-up 即使被路由成 `PROJECT_DETAIL`，也应走同一条 grounded summary 路径。
- Fix:
  在 support runtime 中把 run status + gate reason + whiteboard tail 提炼成结构化 `progress_binding`，并让 frontend reply layer 在 status/progress follow-up 上优先消费这份 binding，输出 concrete progress summary。
- Fix attempt status:
  2026-03-16 scoped fix bound under `ADHOC-20260316-support-status-progress-grounding`.
- Regression test status:
  Covered by `tests/test_frontend_rendering_boundary.py` and `tests/test_support_bot_humanization.py`.
- Prevention:
  任何 user-visible progress/status reply 都不能只依赖 `visible_state` 模板映射；只要 run/whiteboard 已经有具体进展，runtime 就必须把这些字段显式注入 customer-facing summary path。
- Tags:
  support, telegram, progress-grounding, whiteboard, status-reply, runtime

## Example 21

- Symptom:
  用户在 Telegram 里已经明确说过“按之前的大纲走”，但 support bot 既不会在后台进展变化时主动发消息，也会把这类续做请求直接绑定成一个 generic 新 run，随后卡在合同评审。
- Repro:
  1. 在已有历史 support session/backup session 的 Telegram chat 中发送类似 `你能不能重新做一个我之前想要你做的项目`、`就直接按之前的大纲走就行了`。
  2. 观察 support runtime：新 run goal 直接等于这句泛化续做文本，随后用户只能靠不断追问状态。
  3. 在长轮询空闲期间等待后台状态变化，发现 Telegram 不会主动推送任何 grounded update。
- Root cause:
  `scripts/ctcp_support_bot.py` 之前只在收到新用户消息时才会 `process_message()`，没有 idle-phase `advance + digest compare + send_message`；同时 `sync_project_context()` 缺少 archived brief recovery，导致 explicit previous-outline request 被当成一个新的 generic run goal。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::run_telegram_mode` and `scripts/ctcp_support_bot.py::sync_project_context`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`
- Observed fallback behavior:
  用户不追问就收不到进度变化；“之前的大纲/之前的项目”被错误地降格成空泛 goal，新 run 很快卡在合同评审或其它早期 gate。
- Expected correct behavior:
  Telegram idle 轮询应在无用户新消息时继续推进可推进的 run，并在 grounded progress digest 变化时主动发一条具体更新；explicit previous-outline request 应优先恢复 archived session 里的 concrete brief，而不是重复创建 generic run。
- Fix:
  为 support session 增加 notification/resume metadata，在 Telegram idle cycle 里加入 background `ctcp_advance()` 与 progress digest compare，并在 `sync_project_context()` / proactive cycle 中增加 archived previous-outline brief recovery 与必要的 run rebinding。
- Fix attempt status:
  2026-03-16 scoped fix bound under `ADHOC-20260316-support-proactive-progress-and-resume`.
- Regression test status:
  Covered by `tests/test_runtime_wiring_contract.py` and `tests/test_support_bot_humanization.py`.
- Prevention:
  任何“继续之前项目”的能力都必须同时覆盖三件事：history brief recovery、live run rebinding 策略、idle-phase proactive progress push；不要只修某一层 prompt 或只靠人工手动 rebind。
- Tags:
  support, telegram, proactive-update, idle-loop, continuity, previous-outline, runtime

## Example 22

- Symptom:
  用户在 Telegram 里只发一次 `你好`，support bot 先正常回 greeting，随后又因 `SUPPORT_PROGRESS_PUSHED` 主动发出第二条 greeting-like 文案，形成重复寒暄。
- Repro:
  1. 让 support session 绑定一个 active run，并开启 proactive progress push。
  2. 用户发送一条 greeting，例如 `你好`。
  3. 观察 `support_inbox.jsonl` 只有一条新消息，但稍后 `events.jsonl` 仍追加 `SUPPORT_PROGRESS_PUSHED`，且 `support_reply.json` 变成第二条 greeting-like 主动回复。
- Root cause:
  proactive push 复用了 inbox 里的最新用户消息作为 frontend latest-turn 语义；当这条最新消息是 greeting/smalltalk 时，internal reply pipeline 会把主动 push 重新分类成 `GREETING`，从而把本应是 progress update 的消息渲染成第二条问候。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::run_proactive_support_cycle` -> `build_grounded_status_reply_doc`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`
- Observed fallback behavior:
  一条真实用户问候后，bot 会额外主动再发一条“随时可以开始/你说说看要做什么”之类的寒暄。
- Expected correct behavior:
  proactive push 应强制沿用 status/progress 语义；即使最新 inbox turn 是 greeting，后续主动消息也必须呈现为具体进展更新，而不是第二条 greeting。
- Fix:
  为 proactive push 增加 latest-turn status override，避免 customer-facing render path 直接复用最新 greeting；并补 focused regression 锁住这条语义。
- Fix attempt status:
  2026-03-17 scoped fix bound under `ADHOC-20260317-support-proactive-push-greeting-dup-guard`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py`.
- Prevention:
  任何 customer-facing proactive push 都要显式声明自己的 latest-turn semantic purpose，不得默认复用 inbox 里的最后一条用户文本做 conversation re-routing。
- Tags:
  support, telegram, proactive-update, greeting-dup, latest-turn, runtime

## Example 23

- Symptom:
  greeting-dup wording 问题修掉后，用户只发一次 `你好`，bot 仍可能在几秒后主动发出一条具体 progress update，即使 run 状态本身没有新变化。
- Repro:
  1. 让 support session 绑定 active run，且 `notification_state.last_progress_hash` 已记录上一条真实进度摘要。
  2. 用户发送一条 non-project greeting，例如 `你好`。
  3. 观察 greeting turn 自身正常结束后，idle proactive cycle 又把同一份 run 状态当成“新变化”推送一次。
- Root cause:
  `process_message()` 之前会在任何 turn 结束后调用 `remember_progress_notification()`；对于 greeting/non-project turn，`sync_project_context()` 返回空 `project_context`，但 progress digest 仍会基于空 context + `task_summary_hint` 生成一份 synthetic digest，覆盖掉之前记录的真实 run digest。下一轮 idle proactive cycle 读到真实 run context 时，digest 看起来“变了”，于是同状态再次被主动推送。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`
- Observed fallback behavior:
  用户打一声招呼后，没有任何真实 run 进展变化，系统仍会紧跟着主动再发一条已有状态的 progress update。
- Expected correct behavior:
  non-project turn 不应覆盖 `notification_state` 里的最后一条真实 run digest；只有真实 run context 存在时，progress baseline 才允许更新。
- Fix:
  让 `remember_progress_notification()` 只在 `project_context.run_id` 存在时更新 baseline，并补 focused regression 锁住 greeting turn 的 baseline preservation。
- Fix attempt status:
  2026-03-17 scoped fix bound under `ADHOC-20260317-support-proactive-baseline-preserve-on-greeting`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py`.
- Prevention:
  任何 proactive dedupe / notification baseline 都必须明确区分“真实 run digest”和“non-project synthetic context”；不要让 greeting/smalltalk turn 改写工程态去重基线。
- Tags:
  support, telegram, proactive-update, dedupe, greeting, baseline, runtime

## Example 24

- Symptom:
  用户在 Telegram 里追问 `我想要知道我之前那个项目做成什么样子了`，support bot 没有汇报 bound run 的真实进展，反而回成“请提供最新规划文档”。
- Repro:
  1. 让 support session 已绑定一个 active run，并保留已有 `project_brief`。
  2. 发送旧项目状态追问，例如 `我想要知道我之前那个项目做成什么样子了`。
  3. 观察 `support_reply.json`、`support_session_state.json` 和 `artifacts/support_whiteboard.json`。
- Root cause:
  status-query 识别词没有覆盖“之前那个项目做成什么样了”这类旧项目进度追问，导致该句被错误路由成 `PROJECT_DETAIL`；随后 `should_refresh_project_brief()` 只看项目 goal marker，又把这句写回长期 brief，并让 bound run 继续触发新的 planning/file-request 工作。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `frontend/conversation_mode_router.py`, `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  用户看到的是重新补规划文档的问题，session brief 也被错误覆盖，whiteboard 还会追加新的 `file_request/context_pack` 轨迹。
- Expected correct behavior:
  active support session 上的旧项目状态追问应优先走 `STATUS_QUERY` / grounded progress path，直接消费当前 bound run 的状态、whiteboard 和下一步，不得覆盖长期 brief。
- Fix:
  扩展 status-query 识别以覆盖旧项目进度追问，并在 `should_refresh_project_brief()` / `detect_conversation_mode()` 中显式保护这类句子，不让它们重写 `project_brief`。
- Fix attempt status:
  2026-03-17 scoped fix bound under `ADHOC-20260317-support-previous-project-status-grounding`.
- Regression test status:
  Covered by `tests/test_frontend_rendering_boundary.py` and `tests/test_support_bot_humanization.py`.
- Prevention:
  任何“之前那个项目/之前的项目现在怎么样”这类 active-run follow-up，都要同时检查三件事：conversation mode 是否命中 `STATUS_QUERY`、长期 brief 是否保持原项目 goal、以及用户可见回复是否真正消费了 bound run progress。
- Tags:
  support, telegram, status-query, previous-project, brief-memory, runtime

## Example 25

- Symptom:
  support/frontend 明明已经有 conversation mode、session memory zone 和 run binding，但用户一旦插话、改风格或追问结果，前台仍可能像“按最后一句自由回复”的 shell，而不是一个持续推进主任务的前台状态机。
- Repro:
  1. 让 support session 先绑定一个 active run。
  2. 依次发送风格调整、非项目插话、状态追问、结果追问等 turn。
  3. 检查 `support_session_state.json`、`support_prompt_input.md`、`support_reply.json`，会发现旧 runtime 只有零散 memory zone 和 `conversation_mode`，没有单一 frontdesk `state + slots + interrupt_kind + resumable_state` 结构。
- Root cause:
  support runtime 的 continuity 逻辑分散在 `detect_conversation_mode()`、`sync_project_context()`、`build_support_prompt()`、`build_final_reply_doc()` 和 `response_composer` 局部分支里；同时 `状态` 这类宽松词面还会误命中 `状态机` 这类普通工程词，导致主线任务被错分流。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `frontend/conversation_mode_router.py`, `frontend/response_composer.py`
- Observed fallback behavior:
  用户可见 reply 依赖 latest turn shell；style change 只能临时生效；interrupt/resume/decision gating 缺少显式状态；涉及“状态机”的正常需求还可能被误分成 `STATUS_QUERY`。
- Expected correct behavior:
  support entrypoint 应显式持久化并消费 frontdesk state machine、任务槽位、风格 profile 和 interrupt 分类；`状态机` 这类正常工程词不能被误判成 status query。
- Fix:
  增加 `frontend/frontdesk_state_machine.py` 作为显式状态协调层，把它持久化进 `support_session_state.json`，并让 prompt/reply/runtime 消费这份结构；同时收紧 `conversation_mode_router` 的 `状态` 词面，避免误伤 `状态机`。
- Fix attempt status:
  2026-03-17 scoped fix bound under `ADHOC-20260317-support-frontdesk-state-machine`.
- Regression test status:
  Covered by `tests/test_frontdesk_state_machine.py`, `tests/test_runtime_wiring_contract.py`, and `tests/test_support_bot_humanization.py`.
- Prevention:
  任何声称“前台已经任务型化”的能力，都必须同时证明 `state` 已连接到 session persistence、prompt context、reply strategy 和 runtime tests；状态类关键词规则要避免误伤 `状态机` 这类工程名词。
- Tags:
  support, frontend, state-machine, interrupt-recovery, style-profile, routing

## Example 26

- Symptom:
  用户发项目创建需求后，support bot 几秒内回复“项目已准备好并可发包”，但主 run 仍停在 `gate=blocked`，后续并未按同一主流程继续推进。
- Repro:
  1. 在 Telegram support session 发送项目创建句（如“帮我创建一个剧情工具项目”）。
  2. 观察 `support_session_state.json`、`support_t2p_state_machine_report.json` 与绑定 run 的 `RUN.json/status.gate`。
  3. 可见 support 侧先出现 `SUPPORT_T2P_STATE_MACHINE_REPORTED=PASS`，同时 bound run 仍 `status.gate.state=blocked`（例如等待 `artifacts/PLAN_draft.md`）。
- Root cause:
  support runtime 同时存在两条路径：bridge 主流程（bind/record/advance）与 `run_t2p_state_machine` 快速脚手架旁路。快通道先生成 package-ready 语义并进入用户回复，导致“看起来完成了”但主流程还在阻塞。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `docs/10_team_mode.md`
- Observed fallback behavior:
  用户看到“已准备好项目包”，随后又发现项目并未沿主 run 状态机继续推进。
- Expected correct behavior:
  项目型 turn 只允许单主流程：统一走 bridge 绑定 run、记录 turn、advance、消费 gate/status；`gate=blocked` 时只回 grounded 状态与下一步，不给“已交付”语义。
- Fix:
  禁用 support 侧 t2p 快速触发门（`should_trigger_t2p_state_machine`），并在合同文档里写死“禁止快速旁路、只保留主流程状态机”。
- Fix attempt status:
  2026-03-24 scoped fix bound under `ADHOC-20260324-support-single-mainline-state-machine`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py` (`test_t2p_fast_path_trigger_is_disabled_for_project_create_turn`).
- Prevention:
  任何用户可见“已生成/可交付”语义都必须绑定主 run gate/status；禁止在 support 层再引入并行快通道状态源。
- Tags:
  support, telegram, dual-path, state-machine, gate, delivery, runtime-wiring

## Example 27

- Symptom:
  support 会话长期绑定到一个已经不存在的 run；之后用户只回 `确定/继续/开始` 这类短确认词时，系统会新建一个 `goal=确定` 的错误 run，或者在空闲轮询里持续刷 `run_id not found`。
- Repro:
  1. 让 support session 保存一个已经被删除的 `bound_run_id`。
  2. 触发 proactive cycle，或在 Telegram 里继续回复 `确定`、`继续`、`开始`。
  3. 观察 stderr/日志里的 `run_id not found` 持续出现，或新 run 的 `analysis.md` 把 goal 写成确认词。
- Root cause:
  交互式桥接和 proactive 轮询对 `run_id not found` 的恢复逻辑不一致；同时短确认词没有和已有项目上下文绑定，导致 stale run 被清空后直接把确认词当成了新 goal。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::sync_project_context` 和 `scripts/ctcp_support_bot.py::run_proactive_support_cycle`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, `frontend/conversation_mode_router.py`
- Observed fallback behavior:
  用户可见 reply 还在说“我会继续推进”，但 backend 实际没有推进；旧 run 残留还会持续污染 session state 和 proactive 日志。
- Expected correct behavior:
  stale `bound_run_id` 必须在 direct/proactive 两条路径上统一清理；短确认词在已有项目上下文下只能继续/答复当前 run，而不能新建 `goal=确定` 的 run；`PLAN_draft.md` 缺失要进入明确可重试恢复态。
- Fix:
  统一 stale run recovery helper，清空失效绑定并写回 recoverable session/runtime context；给确认类短消息加已有上下文下的 follow-up 路由；对缺失 `PLAN_draft.md` 的 blocked gate 输出 retry-ready recovery doc 并允许自动重试 planner。
- Fix attempt status:
  2026-04-07 scoped repair bound under `ADHOC-20260407-support-session-recovery-and-plan-self-heal`.
- Regression test status:
  Covered by `tests/test_support_bot_humanization.py`, `tests/test_runtime_wiring_contract.py`, `tests/test_support_to_production_path.py`, and `tests/test_frontend_rendering_boundary.py`.
- Prevention:
  任何 support 改动只要碰 run binding 或低信息 follow-up 路由，就必须同时补一个 direct stale-run test 和一个 proactive stale-run test；planner gate 缺件必须输出 recovery hint，不能只留 optimistic progress 话术。
- Tags:
  support, session, stale-run, recovery, routing, plan, proactive

## Example 28

- Symptom:
  用户提交正常的软件项目需求，例如本地可运行的 VN 项目助手，但客服回复却混入点云/无人机/PLY/LAS 等旧领域内容，或者在没有正式 backend reply 时只回“收到，我继续推进”。
- Repro:
  1. 通过 support/frontend 主链提交泛化项目需求或 VN 需求。
  2. 让 provider/backend 缺少 customer-ready reply，或让 frontend PM mode 走默认提问路径。
  3. 观察 `support_reply.json.reply_text` 与 frontend follow-up，出现旧点云默认问题或假进度兜底。
- Root cause:
  `frontend/project_manager_mode.py` 和 `frontend/missing_info_rewriter.py` 仍保留 pointcloud-first 的默认假设；`scripts/ctcp_support_bot.py`、`frontend/response_composer.py`、`frontend/support_reply_policy.py` 在 backend/provider 无正式回复时仍允许乐观 continuation shell。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message` -> `frontend/response_composer.py::run_internal_reply_pipeline`
- Affected modules:
  `frontend/project_manager_mode.py`, `frontend/missing_info_rewriter.py`, `frontend/response_composer.py`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  通用项目被点云默认追问污染；API/backend 无正式回复时仍出现“继续推进”或“本地兜底继续”式误导性文案。
- Expected correct behavior:
  只有显式点云需求才进入点云分支；backend unavailable / blocked / no-formal-reply / low-confidence-fallback 都要用真实状态文案，不能假装已有进展。
- Fix:
  引入显式 domain profiling，把 pointcloud 逻辑只挂到明确关键词；把 provider/backend truth 注入 frontend render 和 reply policy；移除 customer-facing failover optimistic notice。
- Fix attempt status:
  2026-04-08 scoped repair bound under `ADHOC-20260408-support-domain-neutrality-and-truthful-reply-boundary`.
- Regression test status:
  Covered by `tests/test_frontend_rendering_boundary.py`, `tests/test_support_bot_humanization.py`, `tests/test_runtime_wiring_contract.py`, and `tests/test_support_reply_policy_regression.py`.
- Prevention:
  任何 support/frontend 改动只要涉及默认问题、domain inference、fallback reply 或 backend truth，都必须同时补“通用/VN 不被点云污染”和“无正式 reply 不得假装继续推进”两类回归。
- Tags:
  support, frontend, domain-pollution, pointcloud, fallback, truthful-status

## Example 29

- Symptom:
  support run 看起来仍是 `run_status=running`，但真实链路已经卡在 `context_pack.json` 或 `PLAN_draft.md`；同时用户可见状态还可能继续显示旧 blocker 摘要。
- Repro:
  1. 让 planner 或 librarian provider 报告 `executed`，但实际不落地目标产物，例如不生成 `artifacts/PLAN_draft.md`。
  2. 或者先让 `support_runtime_state.json` 记录 `waiting for context_pack.json`，再让 backend status 恢复为 `run_status=running`、`gate_state=open`。
  3. 观察 orchestrator status 与 support-visible reply，前者可能回落成泛化 `waiting for ...`，后者可能继续沿用旧 blocker。
- Root cause:
  `scripts/ctcp_dispatch.py` 之前没有把 “provider 报 executed 但 target 文件不存在” 视为失败；`scripts/ctcp_orchestrate.py::current_gate` 会优先回到泛化缺件判断；`scripts/ctcp_front_bridge.py::_runtime_blocking_reason` 还会在 backend 已恢复后继续复用旧 `blocking_reason`。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::process_message` -> `scripts/ctcp_front_bridge.py::ctcp_get_status` -> `scripts/ctcp_orchestrate.py::current_gate`
- Affected modules:
  `scripts/ctcp_dispatch.py`, `scripts/ctcp_orchestrate.py`, `scripts/ctcp_front_bridge.py`, `scripts/ctcp_librarian.py`, `tools/providers/local_exec.py`
- Observed fallback behavior:
  run 假装仍在 running；planner/librarian 真失败被重新折叠成 `waiting for context_pack.json` / `waiting for PLAN_draft.md`；support 可见状态继续沿用旧摘要。
- Expected correct behavior:
  target artifact 未落地必须沉淀成明确 blocker；bridge refresh 后应清掉过期 blocker；librarian 失败要有结构化 failure artifact。
- Fix:
  把 `executed + missing target` 变成 `exec_failed/target_missing`，让 orchestrator 对缺件时优先保留更具体的 `blocked_reason`，并给 librarian 写 `context_pack.failure.json` 供测试和下游断言。
- Fix attempt status:
  2026-04-08 scoped isolation bound under `ADHOC-20260408-support-chain-breakpoint-isolation`.
- Regression test status:
  Covered by `tests/test_local_librarian.py`, `tests/test_support_runtime_acceptance.py`, and `tests/test_support_to_production_path.py`.
- Prevention:
  任何 support/backend artifact gate 改动，只要 provider 会写 run artifact，就必须补一条 “provider 声称执行成功但 target 缺失” 回归；任何 runtime snapshot refresh 也必须补一条“旧 blocker 不得跨状态恢复残留”的回归。
- Tags:
  support, bridge, orchestrator, librarian, planner, blocker, stale-state, artifact-materialization

## Example 30

- Symptom:
  Telegram 最终回复说“我现在把 zip 包和结果截图发到当前对话”，但用户只看到文本、抽象 overview 图、hash 或内部 artifact 提示，没有真正收到可用 zip 与成品截图。
- Repro:
  1. 让后台 run 达到 verify PASS 并触发 support controller result push。
  2. 检查 Telegram 对话与 `artifacts/support_public_delivery.json`。
  3. 观察 proactive/result push 可能只发送文本，或首图选择 `overview.png` 而不是最终成品图。
- Root cause:
  普通消息路径会执行 delivery action，但 proactive/result push 路径之前只调用文本发送；截图候选按文件遍历顺序发送，未优先选择 final/result/app-home 类成品图；公开回复仍可能保留 stage/artifact/json/hash 等内部语气。
- Affected entrypoint:
  `scripts/ctcp_support_bot.py::run_telegram_mode` and `_emit_controller_outbound_jobs`
- Affected modules:
  `scripts/ctcp_support_bot.py`, `frontend/delivery_reply_actions.py`, `tools/providers/project_generation_source_helpers.py`
- Observed fallback behavior:
  用户看到“会发附件”的承诺，但需要人工介入才真正发送；首图可能只是流程证明图；最终文案还可能暴露内部文件或状态机字段。
- Expected correct behavior:
  任何 public delivery action 都必须产生对应的 `sent` 文件记录；截图首发必须优先 final/result/app-home/preview 类成品图；最终回复只用自然语言说明结果、附件和 README/启动入口。
- Fix:
  把 delivery action 无 sent 视为失败并重试；把 proactive/result push 接到 `emit_public_delivery()`；增加截图候选优先级；生成阶段输出 `final-ui.png`；公开回复遇到内部 marker 时改写为用户可读交付说明。
- Fix attempt status:
  2026-04-10 scoped repair bound under `ADHOC-20260410-real-visual-evidence-and-public-delivery`; 2026-04-11 stopgap follow-up aligned the Telegram-visible delivery wording, hard delivery-plan sent-file checks, screenshot-evidence ordering, and generator default `final-ui.png` naming under the same queue item.
- Regression test status:
  Covered by `tests/test_support_proactive_delivery.py`, `tests/test_support_delivery_user_visible_contract.py`, and `tests/test_project_generation_artifacts.py`.
- Prevention:
  任何声称“已交付”的 support/Telegram 改动都必须同时验证 text、photo、document、`support_public_delivery.json.sent`、首图优先级和用户可读启动说明；只有 json 或文本存在不算交付完成。
- Tags:
  telegram, support, public-delivery, screenshot, zip, humanization, proactive

## Example 31

- Symptom:
  仓库顶层文档已经把 CTCP 定位成 `structured goal-to-delivery`、强调 `demo evidence` 和 `visible progress`，但实际 generation gate、默认 context request、以及 progress rendering 仍按旧主链或 blocker-only 逻辑运行。
- Repro:
  1. 阅读 `README.md`、`docs/01_north_star.md`、`AGENTS.md`，确认主链已声明为 `... -> smoke -> demo evidence -> delivery package`，且 visible progress 应优先展示可见 checkpoint。
  2. 检查 `scripts/project_generation_gate.py`、`tools/providers/project_generation_artifacts.py::build_default_context_request()`、`scripts/ctcp_front_bridge_views.py` / `frontend/progress_reply.py`。
  3. 观察 gate 仍缺 `demo_evidence`、context request 不读新的 purpose docs、progress reply 即使已有 `proof_refs` 也只报 blocker。
- Root cause:
  顶层 authority 文档更新后，没有同步收敛到 generation contract validator、default context read set、以及 progress evidence consumer，导致 repo purpose 和 runtime behavior 分叉。
- Affected entrypoint:
  `tools/providers/project_generation_artifacts.py::build_default_context_request`, `scripts/project_generation_gate.py::_validate_pipeline_contract`, `frontend/response_composer.py` -> `frontend/progress_reply.py::compose_progress_update_reply`
- Affected modules:
  `tools/providers/project_generation_validation.py`, `tools/providers/project_generation_artifacts.py`, `scripts/project_generation_gate.py`, `scripts/project_manifest_bridge.py`, `frontend/progress_reply.py`, `scripts/ctcp_front_bridge_views.py`, `scripts/ctcp_support_bot.py`
- Observed fallback behavior:
  生成链默认上下文更像 implementation-first；pipeline contract 对 `demo evidence` 不可见；用户问进度时即使已有截图/包/验证证据，也可能只收到 blocker/phase 播报。
- Expected correct behavior:
  generation contract、default context、bridge manifest 和 progress reply 都应与新的 repo purpose 一致：主链包含 `demo evidence`，default context 读取新的 purpose/agent authorities，visible progress 优先展示 proof refs/checkpoints。
- Fix:
  在 pipeline contract 和 inferred manifest 中插入 `demo_evidence`；把 `AGENTS.md` 与 `docs/01_north_star.md` 纳入 default context request；让 frontend/support progress reply 消费 `proof_refs` 并显示可见 checkpoint 摘要，同时保留 runtime snapshot 中的 `proof_refs`。
- Fix attempt status:
  2026-04-12 scoped alignment bound under `ADHOC-20260412-mainline-doc-alignment`.
- Regression test status:
  Covered by `tests/test_project_generation_artifacts.py`, `tests/test_backend_interface_contract_apis.py`, `tests/test_frontend_rendering_boundary.py`, and `tests/test_runtime_wiring_contract.py`.
- Prevention:
  任何 repo purpose 或 root contract 的主链更新，都必须同步检查 generation gate、default context request、bridge/render snapshot、以及 progress reply consumer 是否一起收敛；只改顶层 md 不算完成。
- Tags:
  contract-drift, generation, progress, visible-evidence, runtime-wiring, docs-alignment
