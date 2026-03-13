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
  1. 通过 `scripts/ctcp_support_bot.py` 发送一条明确项目需求，例如“我想做一个帮我整理 VN 剧情结构的项目”。
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
  1. 先发送一条明确项目需求，例如 `i want to create a project to help me make vn games, especially in clarify storyline`。
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
  1. 在已绑定 run 的 support session 里先发送真实项目目标，例如“我想做一个帮我理顺 VN 剧情结构的项目”。
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
