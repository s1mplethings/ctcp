# ISSUE_MEMORY（经验库）
记录 AI/人类在迁移/套用过程中遇到的坑点与解决办法。

## 规则
- 遇到任何失败：必须记录“症状→原因→解决→是否可复用为 recipe”
- 记录要包含：平台（Win/Linux）、Qt 版本、构建系统、复现步骤

## 2026-05-01 - Project generation provider attribution can overstate API authorship

- 症状: 用户看到 run/provider ledger 标记 `source_generation provider_used=api_agent`，但生成项目与旧版本几乎完全一致，判断最终源码不是 API agent 直接生成。
- 触发: project-generation `source_generation_report.json` 经 `api_agent.execute()` 后进入本地 `normalize_source_generation_stage()`，由本地 materializer 写出项目文件；旧报告只强调 provider 执行，没有记录 per-file materialization provenance。
- 影响入口: `scripts/ctcp_support_bot.py` -> `scripts/ctcp_front_bridge.py` -> `scripts/ctcp_orchestrate.py` -> `scripts/ctcp_dispatch.py` -> `tools/providers/project_generation_source_stage.py`。
- 影响模块: `tools/providers/project_generation_source_stage.py`, `tools/providers/project_generation_artifacts.py`, `tests/test_project_generation_artifacts.py`。
- 观察到的 fallback/误导行为: `run_responsibility_manifest.json` / provider ledger 容易被解读成 `api_agent` 直接创作最终源码；实际文件可能由 deterministic local materializer 生成。
- 期望行为: run artifact 明确区分 provider/stage execution、local file materialization、optional API content merge，并让 `project_manifest.json` 消费这些字段。
- 解决: source stage 输出 `provider_execution`, `file_materialization`, `file_provenance`, `provenance`；project manifest 转存这些字段。
- 回归: `tests/test_project_generation_artifacts.py::test_project_generation_emits_and_consumes_project_spec_and_capability_plan` 断言 source report 与 manifest 都包含 local materializer provenance，且 `provider_authorship=not_claimed`。
- 状态: fixed in progress; targeted regression passing before full verify.
- recipe: 可复用为 provenance/attribution 修复模式，但暂不单独 skillize，除非后续多个 provider/materializer 边界都需要同类报告。

## 2026-05-02 - Greeting reply downgraded to low-confidence fallback text

- 症状: Telegram 用户发送 `你好` 后，bot 回复 `当前正式回复链没有给出可直接发送的结果...低置信度兜底说明`，而不是正常问候。
- 触发: API provider 失败后降级到 Ollama；Ollama 已产出 customer-ready greeting，但 `support_reply_truth=low_confidence_fallback` 和旧项目上下文让回复策略进入 `guide_recovery`，覆盖了 provider 的正常文本。
- 影响入口: `scripts/ctcp_support_bot.py telegram` -> `frontend/support_reply_policy.py`。
- 影响模块: `frontend/support_reply_policy.py`, `tests/test_support_reply_policy_regression.py`。
- 观察到的 fallback/误导行为: 用户可见回复暴露内部“正式回复链/低置信度兜底”状态，造成 bot 像没有回答。
- 期望行为: `GREETING` / `SMALLTALK` 在 provider 已执行且给出可发送文本时，保持用户可读问候，不被旧项目结果或低置信度元数据改写。
- 解决: intent inference 对 `GREETING` / `SMALLTALK` 优先返回 `acknowledge_user`，仅在 provider/error truth 真失败时进入错误回复。
- 回归: `tests/test_support_reply_policy_regression.py::test_degraded_greeting_keeps_customer_ready_provider_reply_test`。
- 状态: fixed; targeted support reply policy regression, support humanization, support-chain, runtime-wiring, workflow/module/code-health checks, and simlab lite replay passed. Canonical code-profile verify rerun timed out after 900s without a new failing gate after lite replay had passed.
- recipe: 不单独 skillize；这是 support reply policy 的局部路由守卫。

## 2026-05-02 - Fresh project request reused stale completed delivery context

- 症状: Telegram 用户发送 `你帮我做一个本地可运行的 VN 项目助手...` 后，bot 回复 `项目已经整理好了...打开 zip 包`，并重复推送旧 run 的截图/zip 交付话术。
- 触发: support session 已绑定旧 completed/PASS run；`sync_project_context()` 对 `PROJECT_DETAIL` turn 优先复用 `bound_run_id`，没有区分强项目创建语气和显式结果查询。
- 影响入口: `scripts/ctcp_support_bot.py telegram` -> `sync_project_context()` -> `ctcp_front_bridge.ctcp_sync_support_project_turn()`。
- 影响模块: `scripts/ctcp_support_bot.py`, `tests/test_support_bot_stale_delivery_context.py`。
- 观察到的 fallback/误导行为: 新创建请求被旧 `visible_state=DONE` / `frontdesk_state=showing_result` 接管，用户看到完成交付而不是新项目 intake/detail。
- 期望行为: `你帮我做一个...` / `build/create/make` 这类强创建 turn 在旧 run 已 completed/PASS 时应新建或重新绑定 run；只有明确问结果、状态、zip、截图时才复用旧 completed run。
- 解决: added a completed-bound-run supersede guard before project sync records the turn into the old run.
- 回归: `tests/test_support_bot_stale_delivery_context.py::test_sync_project_context_new_create_turn_supersedes_completed_bound_run`。
- 状态: fixed; targeted support regressions, workflow/module/code-health gates, and code-profile verify with lite replay skipped passed. Full code-profile verify without the skip timed out during lite replay after progressing to S28 without summary.
- recipe: 不单独 skillize；这是 support route/state selection 的局部缺陷。

## 2026-05-02 - Local materializer output and repeated delivery replies looked like final custom API work

- 症状: 用户看到新项目请求后收到重复的“项目已经整理好了/打开 zip”交付话术，并且生成项目像旧模板，无法证明每个 agent/API 实际写了业务源码。
- 触发: `source_generation` 已记录 provider execution，但 deterministic local materializer 产物仍可进入 deliverable index 并生成最终 zip；reply policy 在 proactive duplicate delivery 场景可判定 suppressed，但 support bot 没有清空原回复文本。
- 影响入口: `tools/providers/project_generation_source_stage.py` -> `tools/providers/project_generation_provenance.py` -> `tools/providers/project_generation_artifacts.py`; `scripts/ctcp_support_bot.py` -> `frontend/support_reply_policy.py`。
- 影响模块: `tools/providers/project_generation_provenance.py`, `tools/providers/project_generation_artifacts.py`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`。
- 观察到的 fallback/误导行为: 本地 materializer-only 业务文件被最终 zip 打包，用户容易理解成 API agent 已完成定制源码；重复 DONE 上下文会再次发送相同交付话术。
- 期望行为: production 业务源码如果没有 API/provider 内容进入文件，只能保留 evidence/manifest，不能打最终定制项目包；proactive 重复交付应真正 suppressed；过长回复应压缩。
- 解决: provenance 增加 `source_customization_completion` 交付门；deliverable index 在 `final_delivery_allowed=false` 时不生成 `final_project_bundle.zip`；reply policy 增加长度压缩和 duplicate delivery suppress；support bot 尊重 suppressed 并清空回复。
- 回归: `tests/test_project_generation_provenance.py`, `tests/test_support_reply_policy_regression.py`。
- 状态: targeted regressions passing before full verify.
- recipe: 可复用为 provider/materializer attribution + delivery gating 修复模式；暂不单独 skillize。

## 2026-05-03 - Production source generation still emitted local template files before final delivery block

- 症状: 虽然 final zip 已经会因 materializer-only provenance 被阻止，但 production source generation 仍会调用 `materialize_business_files()` 并写出本地模板业务文件。
- 触发: `tools/providers/project_generation_source_stage.py::normalize_source_generation_stage()` 在 validation 前无条件调用本地 deterministic business materializer。
- 影响入口: project generation `source_generation` stage。
- 影响模块: `tools/providers/project_generation_source_stage.py`, `tools/providers/project_generation_provenance.py`, `tests/test_project_generation_provenance.py`。
- 观察到的 fallback/误导行为: 用户要求完全不要本地模板时，系统仍会在 run_dir 中留下本地模板项目，只是在后续交付阶段阻止 final bundle。
- 期望行为: production 项目生成在缺少 provider-authored source files 时应在 source stage 阻塞，不写本地业务模板文件。
- 解决: production path 在写出 spec/capability 后直接返回 blocked source-generation report；local materializer import/call 仅保留在非 production/benchmark fallback 路径；provenance strategy 记录为 `disabled_local_templates`。
- 回归: `tests/test_project_generation_provenance.py::test_production_source_generation_blocks_before_local_template_materialization_test`。
- 状态: fixed in progress; targeted regression pending full verify.
- recipe: 可复用为“先阻断 fallback 产物，再报告缺 provider source”的生成主链修复模式。

## 2026-05-04 - Formal API source generation can fail only on long transport calls

- 症状: formal API-only VN run 可以通过 plan/review/freeze 等 API 阶段，但到 `chair/source_generation` 时没有落地 `artifacts/source_generation_report.json`，run 停在 `waiting for source_generation`。
- 触发: 长 source-generation 请求经 `api.gptsapi.net` 代理调用外部 API；同一 run 内重试多次出现 Cloudflare 520、Cloudflare 504 和 `[SSL: TLSV1_ALERT_PROTOCOL_VERSION]`。
- 影响入口: `scripts/ctcp_orchestrate.py advance` -> `scripts/ctcp_dispatch.py` -> `tools/providers/api_agent.py` -> `scripts/externals/openai_agent_api.py`。
- 影响模块: `llm_core/providers/api_provider.py`, `llm_core/clients/openai_compatible.py`, `tools/providers/api_agent.py`。
- 观察到的 fallback/误导行为: 如果只看前序 provider ledger，会误以为正式 API 链已经能生成源码；实际 source-generation 还没有拿到 provider 响应，不能进入源码验证。
- 期望行为: 短 API 探针可证明凭证/基础连接可用；长 source-generation 失败必须明确记录为 API transport blocker，并阻止本地模板兜底冒充成功。
- 解决: 当前任务仅记录证据；下一步最小修复方向是缩短/分块 source-generation 请求、针对 TLS/Cloudflare 错误做更保守退避，或切换稳定 API endpoint/model。
- 回归: live run `20260504-104454-103863-orchestrate`; direct small code-output probe returned a valid `main.py` JSON payload, while source-generation attempts failed before target artifact materialization.
- 状态: open; API path is connected for small calls but not reliable for long source-generation calls.
- recipe: 可复用为“先用小探针区分 API 基础连接和长请求生成能力，再用 provider ledger/target artifact 判断是否真正生成源码”的诊断流程。
