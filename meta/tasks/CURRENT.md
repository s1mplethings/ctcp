# Task - markdown-contract-drift-fix

## Queue Binding
- Queue Item: `L0-PLAN-001`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context
- Goal: fix Markdown contract drift with contract-first, script-aligned rules.
- Scope:
  - unify verify naming and authority across core docs,
  - align headless mainline narrative and downgrade GUI to optional path,
  - normalize maintainable markdown structure for core contract docs,
  - repair doc index / contracts index coverage and queue-discipline linkage.
- Out of scope:
  - product behavior refactor,
  - runtime/orchestrator feature changes.

## DoD Mapping (from queue + current request)
- [x] DoD-1: verify entrypoint + verify artifact naming are unified and script-aligned across required docs.
- [x] DoD-2: README/00_CORE/02_workflow/12_modules_index share one headless-first mainline; GUI is optional path.
- [x] DoD-3: doc index and contracts index cover required key documents/artifacts.
- [x] DoD-4: project plan/task template/current binding removes `N/A` escape and forms queue-task-report closure.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A (repo-local contract sync)`
- [x] Code changes allowed: `N/A (docs/meta/scripts for doc index only)`
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: unify verify contract + headless mainline narrative.
2) Update index contracts (`sync_doc_links.py`, README index block, contracts index).
3) Fix planning-discipline links across project plan/template/current/queue.
4) Run `python scripts/sync_doc_links.py --check` and `scripts/verify_repo.ps1`.
5) Record readlist/plan/changes/verify/demo in `meta/reports/LAST.md`.

## Notes / Decisions
- Canonical verify artifact is `artifacts/verify_report.json`; `proof.json` is downgraded to compatibility.
- `verify_repo.*` remains the only DoD gate entrypoint.
- Direct user request without queue item should be modeled as `ADHOC-YYYYMMDD-<slug>`, not `N/A`.
- Current verify status is blocked by environment/test failures outside this docs-only patch scope (recorded in `meta/reports/LAST.md`).

## Update 2026-03-08 - 客服回复内置多阶段流水线 + 单一公开输出闸门

### Context
- 用户请求：将 frontend/customer-bot 回复链路改造成“内部多阶段分析/草拟/审核/脱敏”，并保证只有最终审核后的回复可对用户可见。
- 本次目标：代码级实现（非 prompt-only），覆盖 `telegram_cs_bot` 与 `ctcp_support_bot` 两条客服输出链路。

### DoD Mapping (from request)
- [x] DoD-1: 新增结构化内部回复状态对象并落地五阶段流水线（requirement -> draft -> review -> sanitize -> final）。
- [x] DoD-2: 单一公开输出闸门：支持链路对用户发言仅经统一 gate 发送，内部阶段不直接发送。
- [x] DoD-3: 严禁内部文本泄漏到用户回复（command failed/rc/stack trace/CONTEXT 等）。
- [x] DoD-4: 项目经理口径：优先提炼高信息需求、内部补默认、仅保留 1-2 个关键问题、避免重复提问。
- [x] DoD-5: 增补回归测试并通过相关客服/前端边界测试。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first update included (`meta/tasks/CURRENT.md` + `meta/reports/LAST.md`)
- [x] Targeted tests pass (`frontend_rendering_boundary` / `telegram_cs_bot_employee_style` / `support_bot_humanization` / `ctcp_support_bot --selftest`)
- [ ] `scripts/verify_repo.*` full pass（待本轮复检记录）

### Plan
1) 在 `frontend` 渲染层引入内部流水线状态对象与分阶段处理函数。
2) 将 `tools/telegram_cs_bot.py` 的客服发送路径改为“统一渲染 + 单一公开输出 gate”。
3) 将 `scripts/ctcp_support_bot.py` 也接入同一渲染流水线，替换旧三段标签 fallback。
4) 补充/更新边界测试，回归执行并记录结果。
5) 运行 `scripts/verify_repo.ps1` 并记录首个失败点或通过结果。

## Update 2026-03-07 - Telegram 客服自测（selftest + 回归）

### Context
- 用户请求：`自己测试一下telgram的客服的情况`。
- 本次目标：仅执行 Telegram 客服自测与相关回归验证，输出可审计结果；不做业务代码改动。

### DoD Mapping (from request)
- [x] DoD-1: 运行 `python scripts/ctcp_support_bot.py --selftest` 并通过。
- [x] DoD-2: 运行 Telegram 客服相关 Python 单测集合并通过。
- [x] DoD-3: 运行 `scripts/verify_repo.ps1`，记录首个失败点与证据路径。
- [x] DoD-4: 将 Readlist/Plan/Changes/Verify/Questions/Demo 落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local verify only)`
- [x] Code changes allowed: `N/A（本次仅任务/报告落盘）`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 读取 CTCP 必读契约与当前任务门禁。
2) 执行 Telegram 客服脚本离线 `--selftest`。
3) 执行客服相关回归单测（support/telegram）。
4) 执行 `scripts/verify_repo.ps1` 并锁定首个失败点。
5) 将证据与最小修复策略写入 `meta/reports/LAST.md`。

## Update 2026-03-07 - Telegram 客服高级强度测试（扩展矩阵）

### Context
- 用户追加请求：`测试多一点，高级一点`。
- 本次目标：在已有自测基础上扩展高强度测试矩阵（循环稳定性 + 全量回归 + 自定义压力回放），并保留可审计证据链。

### DoD Mapping (from request)
- [x] DoD-1: 执行高频稳定性循环测试（`ctcp_support_bot --selftest` 多次循环）。
- [x] DoD-2: 执行 Telegram 客服相关全量回归（support suite / router+stylebank / telegram dataset+intent+employee style）。
- [x] DoD-3: 执行高级压力回放（多会话、中英混合、边界语句）并输出结构化统计报告。
- [x] DoD-4: 执行 `scripts/verify_repo.ps1`，记录首个失败点与最小修复路径。
- [x] DoD-5: 将 Readlist/Plan/Changes/Verify/Questions/Demo 落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local test expansion)`
- [x] Code changes allowed: `N/A（本次仅任务/报告落盘）`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 扩展稳定性回放：执行 `selftest` 循环并输出 JSON 报告。
2) 扩展回归覆盖：全跑 support/telegram 相关单测集合。
3) 执行高级压力回放：区分“含管理命令”和“纯自然会话”两组并记录统计差异。
4) 运行 `scripts/verify_repo.ps1`，收敛到首个失败 gate。
5) 回填报告与证据路径到 `meta/reports/LAST.md`。

## Update 2026-03-07 - Telegram 客服继续测试（Wave 2）

### Context
- 用户追加请求：`继续测试`。
- 本次目标：在既有高级测试基础上继续提高样本量与稳定性，验证“长循环 + 回归复跑 + 门禁复检”一致性。

### DoD Mapping (from request)
- [x] DoD-1: `ctcp_support_bot --selftest` 进行更大规模循环并保持 100% 通过。
- [x] DoD-2: support/telegram 相关回归测试集再次全量通过。
- [x] DoD-3: 追加高强度压力回放（含命令场景 + 纯自然会话场景）并输出结构化统计文件。
- [x] DoD-4: 复跑 `scripts/verify_repo.ps1` 并记录首个失败点与证据路径。
- [x] DoD-5: 将本轮 Readlist/Plan/Changes/Verify/Questions/Demo 落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local testing continuation)`
- [x] Code changes allowed: `N/A（本次仅任务/报告落盘）`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 执行 `selftest` 50 次循环并保存结果到外部 report。
2) 重跑 support/telegram 相关回归单测集合。
3) 执行 Wave 2 压力回放（`with_commands` 与 `no_commands` 双报告）。
4) 复跑 `scripts/verify_repo.ps1` 并解析失败场景详情。
5) 将结果与最小修复建议写入 `meta/reports/LAST.md`。

## Update 2026-03-07 - 模拟用户对话生成类人测试集（Dialogue Sim V1）

### Context
- 用户请求：`我想要类人的，你可以做用户，然后模拟对话生成案例生成测试集吗`。
- 本次目标：新增“模拟用户多轮对话”数据集，并接入自动化回放测试，作为类人口径回归基线。

### DoD Mapping (from request)
- [x] DoD-1: 新增模拟用户多轮对话 fixture（含中英混合与不同角色语气）。
- [x] DoD-2: 新增数据驱动测试，逐轮回放并校验基础对话卫生（非空、无内部泄漏、问句上限）。
- [x] DoD-3: 新增测试与现有 Telegram/support 回归可同时通过。
- [x] DoD-4: 运行 `scripts/verify_repo.ps1` 并记录首个失败点与证据路径。
- [x] DoD-5: 将 Readlist/Plan/Changes/Verify/Questions/Demo 落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local simulated dialogues)`
- [x] Code changes allowed: `Yes（tests/fixtures + tests）`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 生成模拟用户多轮对话案例（Dialogue Sim V1）。
2) 新增 fixture 文档与 JSONL 数据集。
3) 新增数据驱动回放测试并校验类人对话基础指标。
4) 运行相关回归测试与 `scripts/verify_repo.ps1`。
5) 将结果、证据路径和最小修复建议写入 `meta/reports/LAST.md`。

## Update 2026-02-26 - scaffold-pointcloud concrete V2P baseline

### Context
- Upgrade generated `templates/pointcloud_project/minimal` project from placeholder `run_v2p.py` to concrete numpy-only baseline pipeline + deterministic synthetic fixture + voxel-Fscore evaluation.
- Keep CI deterministic/light and keep scope minimal (templates/tests/meta only).

### DoD Mapping (from request)
- [x] DoD-1: generated project includes concrete `scripts/run_v2p.py` depth backprojection + voxel downsample + PLY + scorecard.
- [x] DoD-2: generated project includes deterministic `scripts/make_synth_fixture.py` and `scripts/eval_v2p.py`.
- [x] DoD-3: generated project includes synth pipeline test `tests/test_pipeline_synth.py` with `voxel_fscore >= 0.8`.
- [x] DoD-4: generated project dependencies include `numpy`; semantics fixture produces `cloud_sem.ply`.

### Plan
1) Docs/Spec first: record task/report update for this run.
2) Implement template scripts and dependency updates.
3) Update template tests and scaffold expectations.
4) Run targeted unit tests and `scripts/verify_repo.ps1`.
5) Record verification evidence in `meta/reports/LAST.md`.

## Update 2026-02-27 - V2P fixture auto-acquire + cleanliness hardening

### Context
- Add deterministic fixture acquisition flow for `cos-user-v2p` (`auto|synth|path`) with discover-or-ask behavior.
- Harden pointcloud template/scaffold cleanliness to exclude caches and runtime artifacts from manifests and generated bundles.

### DoD Mapping (from request)
- [x] DoD-1: add `tools/v2p_fixtures.py` with discover + ensure flow and deterministic dialogue fallback.
- [x] DoD-2: wire fixture flow into `cos-user-v2p` args/plan/report and write `artifacts/fixture_meta.json`.
- [x] DoD-3: harden template hygiene + scaffold manifest exclusions + generated project clean utility.
- [x] DoD-4: add/adjust tests for fixture discovery and cos-user synth fixture flow.
- [x] DoD-5: add behavior doc/index entry for fixture acquisition + cleanliness.

### Plan
1) Doc-first update in task/report.
2) Implement fixture helper module and orchestrator/testkit integration.
3) Implement template hygiene and clean utility script/test.
4) Add CTCP tests and behavior catalog entry.
5) Run targeted tests and `scripts/verify_repo.ps1`; record first failure and minimal fix if needed.

## Update 2026-02-27 - Telegram CS API router + APIBOT summary

### Context
- 用户反馈当前 Telegram bot 更像“记录器”，希望升级为“客服型”对话入口：接入 API 做意图理解，并生成可投递给其他 agent 的总结。
- 约束：保持可选工具属性，不改变 CTCP 核心默认离线路径和 verify 入口。

### DoD Mapping (from request)
- [x] DoD-1: 新增 `tools/telegram_cs_bot.py`（stdlib + 本仓库 API 客户端）并支持对话式入口。
- [x] DoD-2: API 客服路由可将自然语言映射为 `status/advance/outbox/bundle/report/lang/note`。
- [x] DoD-3: 生成 `artifacts/API_BOT_SUMMARY.md` 与 `inbox/apibot/requests/REQ_*.json`，并在 agent_request 派发时附带 summary tail。
- [x] DoD-4: 维持 outbox/question/Target-Path 回写、agent bridge requests/results、TRACE/bundle 主动推送。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - my_test_bot 回复乱码防护（编码噪声兜底）

### Context
- 用户反馈 Telegram 会话中出现明显乱码（`���`）的长段回复，影响客户可读性与信任感。
- 目标：在不改变主流程的前提下，为用户通道增加编码噪声检测与兜底，确保看到的始终是可读文本。

### DoD Mapping (from request)
- [x] DoD-1: 用户回复净化链路可识别并剔除明显编码噪声行（含大量 `�`）。
- [x] DoD-2: 若问题文本或追问出现编码噪声，自动回退为默认可读追问，不向用户暴露乱码。
- [x] DoD-3: 新增最小单测覆盖乱码场景，验证输出不含 `�` 且保留自然客服口径。
- [x] DoD-4: `scripts/verify_repo.ps1` 通过并记录到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - 客服 bot 手工高频对话压力测试（日常语 + 工作语）

### Context
- 用户要求“手动大量测试客服 bot 是否可以用正常日常语言和工作语言与客户交流”。
- 约束：本次仅执行手工压力测试与验收，不改代码逻辑；唯一验收入口保持 `scripts/verify_repo.ps1`。

### DoD Mapping (from request)
- [x] DoD-1: 完成高频手工回放（覆盖日常语与工作语，中文为主，含英文样本）。
- [x] DoD-2: 输出可审计测试结论（通过项/失败项/典型样例/风险）。
- [x] DoD-3: 运行 `scripts/verify_repo.ps1` 并记录首个失败点或通过结果。
- [x] DoD-4: 将 Readlist/Plan/Changes/Verify/Demo 完整落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed: N/A（本次仅文档/报告更新）
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - my_test_bot 对话输出去机械化（双通道）

### Context
- 用户反馈 my_test_bot 对话仍夹杂内部事件/文件名（如 `guardrails_written`、`RUN.json`），影响客户体验。
- 目标：默认用户回复只保留负责人口吻三段式；内部细节仅落 run_dir ops/debug 通道。

### DoD Mapping (from request)
- [x] DoD-1: 默认聊天不输出内部 key/path/log 痕迹（`TRACE/outbox/RUN.json/guardrails` 等）。
- [x] DoD-2: 统一用户回复为“结论 -> 方案 -> 下一步（仅 1 个问题）”。
- [x] DoD-3: 引入回复双通道结构（`reply_text/next_question/ops_status`），ops 写入 run_dir 日志。
- [x] DoD-4: 增加显式进度开关：用户发送“查看进度”/`debug`（或 `/debug`）才看里程碑摘要；默认关闭自动推进播报。
- [x] DoD-5: 新增最小单测覆盖净化器与 ops 保留。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-01 - 客户可理解的项目进度口径

### Context
- 用户要求项目播报直接可被客户理解，重点是“现在打算做什么功能、做完什么功能、关键问题是什么”。  

### DoD Mapping (from request)
- [x] DoD-1: `status` 输出包含“现在打算做 / 刚做完 / 关键问题”三段式。
- [x] DoD-2: `advance` 输出改为客户口径，避免仅给内部流水状态。
- [x] DoD-3: TRACE 主动推送优先总结“Done / Doing / Key issue”。
- [x] DoD-4: 增加测试覆盖新口径函数。

## Update 2026-03-01 - USER_NOTES 回显降噪

### Context
- 用户反馈聊天中频繁出现 `已记录到 USER_NOTES: ...`，影响对话连续性。

### DoD Mapping (from request)
- [x] DoD-1: 自然聊天写入 `USER_NOTES` 时默认不回显文件路径。
- [x] DoD-2: 保留可配置能力（`CTCP_TG_NOTE_ACK_PATH=1` 可恢复路径回显）。
- [x] DoD-3: `/note` 显式命令行为保持不变。
- [x] DoD-4: 增加测试覆盖默认静默与可开启回显两种模式。

## Update 2026-03-01 - 仅保留全自动推进模式

### Context
- 用户要求 bot 不再停等“继续”指令；在无待决问题时必须自动推进项目流程。

### DoD Mapping (from request)
- [x] DoD-1: 运行配置固定为全自动推进，不再依赖 `CTCP_TG_AUTO_ADVANCE` 开关。
- [x] DoD-2: 每个 tick 在无待决事项且非终态时自动执行一步 `advance`。
- [x] DoD-3: 决策提示文案去掉“你可以发送继续”，改为“我会自动推进”。
- [x] DoD-4: 增加测试覆盖 `Config.load` 强制全自动与空闲自动推进行为。
- [x] `scripts/verify_repo.ps1` final pass recorded

### Follow-up (UX polish)
- [x] `advance/status` 在对话中改为自然语言总结，减少原始日志直出。
- [x] 保留关键信息：阻塞原因、owner、target-path、run 状态、迭代信息。
- [x] 修复 API agent 编码异常（surrogate 字符导致的 `UnicodeEncodeError`）以恢复连续推进。

## Update 2026-03-01 - Telegram 客服“员工感”增强

### Context
- 用户希望客服 bot 更像真实员工，而不是仅做命令路由或消息记录。
- 约束：保持现有 CTCP run_dir 协作协议不变，不新增第三方依赖，不改变 verify 入口。

### DoD Mapping (from request)
- [x] DoD-1: 普通对话进入 note 分支时，先给出员工式确认/推进回复，而非仅回写路径提示。
- [x] DoD-2: API 路由 prompt 加入“确认-行动-下一步”客服口吻约束，并支持可选 follow-up 澄清问题。
- [x] DoD-3: 状态消息包含 run state，提升客户感知。
- [x] DoD-4: 新增测试覆盖员工式回复核心逻辑。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - CTCP Support Bot（CEO口径 + 双通道）

### Context
- 用户要求新增一个“更像 CEO/团队负责人”的客服 bot：
  - 对用户只输出自然客服结论，不夹杂任何日志。
  - 对内复用 CTCP provider 体系（本地 ollama / 外部 codex/api）进行分析与执行。
- 约束：不新增第三方依赖；run_dir 必须在仓库外；verify 入口保持 `scripts/verify_repo.*`。

### DoD Mapping (from request)
- [x] DoD-1: 新增 `scripts/ctcp_support_bot.py`，支持 `--stdin` 与 `telegram --token` 两种模式。
- [x] DoD-2: 新增 `agents/prompts/support_lead_reply.md`，强制 JSON 输出和“结论->方案->下一步”口径。
- [x] DoD-3: 新增 `docs/dispatch_config.support_bot.sample.json`，可配置本地 ollama 与外部 codex 路由。
- [x] DoD-4: 实现双通道输出：用户只收 `reply_text`；provider/debug 细节写入 `${run_dir}/logs/support_bot.*.log`。
- [x] DoD-5: 提供离线 `--selftest`，验证 `artifacts/support_reply.json` 产出与回复脱敏规则。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - Telegram CS Bot Human-like + Local Router -> API Handoff (CTCP 2.7.0)

### Context
- 用户要求把 `tools/telegram_cs_bot.py` 从“单一路由+模板式回复”升级为“更像真人客服”的对话链路：
  - 每轮主动推进，不等“继续”
  - 分段自然表达（2-4 段），避免条目列表腔
  - 会话状态连续记忆（summary/confirmed/open questions）
  - 本地 router 先决策，必要时 handoff 到 API agent
  - 保持用户通道干净，ops 通道留痕

### DoD Mapping (from request)
- [x] DoD-1: 新增 `support_session_state.json` 状态链路并每轮读写。
- [x] DoD-2: 新增 `support_lead_router` prompt 与 router->handoff 代码路径（含失败优雅降级）。
- [x] DoD-3: 回复满足“非列表、分段、措辞稳定变化、每轮推进”并保持 sanitize 不退化。
- [x] DoD-4: 更新 `docs/dispatch_config.support_bot.sample.json` 与 `docs/10_team_mode.md` 说明。
- [x] DoD-5: 新增最小单测覆盖 sanitize / 分段非列表 / router-handoff 落盘。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - my_test_bot 输出去“机械重复追问”（真人感修复）

### Context
- 用户反馈 my_test_bot 在 blocked 状态会重复发送同类消息，且反复追问“继续自动推进可以吗”，对话观感像脚本循环。
- 目标：保留自动推进能力，但把 blocked 场景改为“聚焦一次关键输入 + 不重复催问 + 输入后立即续推”。

### DoD Mapping (from request)
- [x] DoD-1: `advance blocked` 文案从“自动推进确认问句”改为“当前卡点 + 需要补齐的信息”，不再反复问“可以吗”。
- [x] DoD-2: 同一 blocked 原因短时间内不重复推送同类消息，避免一分钟内多条重复播报。
- [x] DoD-3: 自动推进在 blocked 冷却期内暂停，用户补充新输入后自动清除冷却并继续推进。
- [x] DoD-4: 增加最小单测覆盖（blocked 冷却/去重 + 手动 advance 后不二次自动推进）。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-02 - my_test_bot 真人客服化（寒暄优先 + 会话记忆 + 去工程口吻）

### Context
- 用户反馈当前会话回复仍偏工程流水：例如“我已经推进到下一里程碑”“先按 patch 路径推进吗”，不像真人客服。
- 目标：把 `tools/telegram_cs_bot.py` 调整为更像真人客服的口径，支持日常寒暄、可感知记忆、减少机械追问。
- 约束：不新增第三方依赖；保持 run_dir 协议与 `scripts/verify_repo.ps1` 唯一验收入口不变。

### DoD Mapping (from request)
- [x] DoD-1: 纯寒暄输入（你好/谢谢/你能做什么等）优先本地响应，不触发工程路由问句。
- [x] DoD-2: 新增 slot-like 会话记忆（`memory_slots`）并在回复中可用于跨轮延续语境。
- [x] DoD-3: 去除默认工程口吻追问（如 patch/verify 路径确认），改为客服自然澄清。
- [x] DoD-4: 增加重复追问抑制，避免同一问题连续多轮重复。
- [x] DoD-5: 增加最小单测覆盖寒暄优先、记忆槽位更新、追问去重。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged: `meta/externals/20260302-telegram-cs-human-memory.md`
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-03 - my_test_bot 寒暄误记忆修复（不再把“你好”当项目主题）

### Context
- 用户反馈对话首句“你好”后，bot 回复“我记得你在推进‘你好’”，明显不符合真人客服语感。
- 根因：会话状态更新时把寒暄文本写入 `user_goal`，后续 `smalltalk_reply` 直接把该值当主题回显。

### DoD Mapping (from request)
- [x] DoD-1: 寒暄文本不再写入 `user_goal`。
- [x] DoD-2: `smalltalk_reply` 对“你好/谢谢/what can you do”等伪主题自动忽略，不回显为“正在推进”。
- [x] DoD-3: 新增回归测试覆盖“寒暄不写目标 + 正常需求可写目标”。
- [x] DoD-4: `scripts/verify_repo.ps1` 全门禁通过。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-03 - Telegram CS Bot 2.7.0：local-first router + stylebank + session memory 对齐

### Context
- 用户要求把客服 bot 升级为“更像真人 + 主动推进 + 本地路由后按需升级 API”，并保持 CTCP 核心契约不变（run_dir 外置、双通道日志、可验证闭环）。
- 当前实现已具备基础 router/handoff/memory，但路由 schema、StyleBank 选择因子与测试入口还未完全对齐目标交付。

### DoD Mapping (from request)
- [x] DoD-1: `agents/prompts/support_lead_router.md` 升级为严格 JSON 路由契约（`route/intent/confidence/followup_question/style_seed/risk_flags`，local-first，最多一个问题）。
- [x] DoD-2: `agents/prompts/support_lead_reply.md` 升级为 2-4 段自然表达 + `style_seed` 入口 + 禁止列表风格，同时保持单 JSON 输出。
- [x] DoD-3: `tools/telegram_cs_bot.py` 接入新路由枚举（`local/api/need_more_info/handoff_human`）与优雅降级；新增会话状态字段 `last_intent/last_style_seed` 并持续更新。
- [x] DoD-4: 新增 `tools/stylebank.py`，实现 `sha256(chat_id|intent|turn_index|style_seed)` 的确定性措辞变体选择，并接入 bot。
- [x] DoD-5: 新增 `tests/test_support_router_and_stylebank.py`，覆盖 StyleBank 确定性、路由升级逻辑与用户输出断言。
- [x] DoD-6: 文档补充路由/升级/查看进度说明，不暴露内部绝对路径。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-03 - my_test_bot 执行目标对齐（让 bot 知道“要干什么”）

### Context
- 用户明确要求：核心是让 bot 持续知道“当前要干什么”。
- 问题：仅靠自然对话历史会漂移，缺少稳定的“执行目标 + 下一步动作”字段，导致回复偶发泛化。

### DoD Mapping (from request)
- [x] DoD-1: 会话状态新增执行对齐字段：`execution_goal` / `execution_next_action`。
- [x] DoD-2: 每轮真实需求输入会更新执行对齐字段；寒暄输入不污染该字段。
- [x] DoD-3: 回复 prompt 注入 `execution_focus`，强制模型围绕“目标+下一步”组织内容。
- [x] DoD-4: 增加最小单测覆盖执行对齐字段与 prompt 注入行为。
- [x] DoD-5: `scripts/verify_repo.ps1` 全门禁通过。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-03 - 项目创建对话回放修复（去“下一里程碑”空泛回复）

### Context
- 用户提供真实会话样本：
  - `你好` -> 正常
  - `我想要创建一个项目` -> 回复变成“我已经推进到下一里程碑，并会继续执行”
- 要求：做完整项目生成对话测试并修正该问题。

### DoD Mapping (from request)
- [x] DoD-1: 新增“完整对话回放”测试，覆盖两轮对话（寒暄 -> 创建项目）。
- [x] DoD-2: 当上游回复乱码或被净化后空白时，不再回“下一里程碑”模板句。
- [x] DoD-3: 对“创建项目”意图新增专用客服兜底回复（包含可执行下一步与单一关键问题）。
- [x] DoD-4: `scripts/verify_repo.ps1` 全门禁通过。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-04 - 清理 Telegram CS Bot 过时路由兼容代码

### Context
- 用户要求“按照文档检查并清理不要的代码”，并确认“直接全部清理”。
- 文档约束已明确 router 契约使用 `route/intent/confidence/followup_question/style_seed/risk_flags`，本地代码仍保留旧兼容字段和旧路由别名处理。

### DoD Mapping (from request)
- [x] DoD-1: 清理 `tools/telegram_cs_bot.py` 中过时路由兼容输出字段（`route_legacy`）与旧字段回退逻辑（`need_user_confirm`）。
- [x] DoD-2: 清理旧路由别名兼容分支（`api_handoff` / `local_reply`），统一使用文档契约路由值。
- [x] DoD-3: 同步更新相关测试输入与断言，避免继续依赖过时字段/路由名。
- [x] DoD-4: 通过 `scripts/verify_repo.ps1` 全门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-04 - 继续按文档清理 StyleBank 旧路由别名

### Context
- 用户要求继续“按照 MD 修复项目”。
- 当前代码中 `tools/stylebank.py` 仍保留 `api_handoff/local_reply` 旧路由别名兼容，与当前文档路由契约不一致。

### DoD Mapping (from request)
- [x] DoD-1: 移除 `tools/stylebank.py` 中旧路由别名（`api_handoff`、`local_reply`）兼容映射。
- [x] DoD-2: 保持 StyleBank 的确定性行为不退化（现有测试通过）。
- [x] DoD-3: 通过 `scripts/verify_repo.ps1` 全门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-04 - 按要求执行全功能测试（Lite + Full Gate）

### Context
- 用户要求“按照要求对所有的功能做测试”。
- 按仓库契约，验收入口统一为 `scripts/verify_repo.ps1`，并且 `CTCP_FULL_GATE=1` 需覆盖 full checks 路径。

### DoD Mapping (from request)
- [x] DoD-1: 执行默认 `scripts/verify_repo.ps1`（Lite 路径）并记录完整结果。
- [x] DoD-2: 执行 `CTCP_FULL_GATE=1` 的 `scripts/verify_repo.ps1`（Full 路径）并记录完整结果。
- [x] DoD-3: 将测试命令、返回码和关键输出落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed: N/A（本次仅测试与文档记录）
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-04 - 自建 Telegram bot 测试集并按失败点修复

### Context
- 用户要求“自己制作 telegram bot 的测试集，然后修改它”。
- 目标：新增一组数据驱动用例，覆盖实际会话入口，并根据首个失败点做最小修复。

### DoD Mapping (from request)
- [x] DoD-1: 新增 Telegram bot 测试集（fixture）并接入自动化测试。
- [x] DoD-2: 新增测试能稳定复现至少一个真实行为缺陷。
- [x] DoD-3: 修改 `tools/telegram_cs_bot.py`，让新测试通过且不回归现有测试。
- [x] DoD-4: 通过 `scripts/verify_repo.ps1` 门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-04 - 继续扩展 Telegram bot 测试集

### Context
- 用户要求“继续扩展测试集”。
- 目标：在已落地的 `telegram_bot_dataset_v1` 基础上扩展覆盖面（中英文、无 run/有 run、status/outbox/report/decision/advance/cleanup/create-run）。

### DoD Mapping (from request)
- [x] DoD-1: 将 `tests/fixtures/telegram_bot_dataset_v1/cases.jsonl` 扩展到 12+ 条并覆盖多意图分支。
- [x] DoD-2: 新增断言字段与数据集说明保持一致（`contains_any/contains_all/not_contains_any`）。
- [x] DoD-3: 新增数据集通过回归测试，不破坏既有 Telegram 测试。
- [x] DoD-4: 通过 `scripts/verify_repo.ps1` 全门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-05 - 继续加大强度测试（按 MD 新增）

### Context
- 用户要求“继续加大强度测试，按照 MD 新增”。
- 目标：提升 Telegram bot 测试强度与覆盖密度，补齐更系统的意图矩阵与更多数据驱动回放样例。

### DoD Mapping (from request)
- [x] DoD-1: 新增意图矩阵测试，覆盖中英文和高频自然短句分流。
- [x] DoD-2: 扩展 `telegram_bot_dataset_v1` 至 30+ 条样例，覆盖无 run/有 run 的更多边界输入。
- [x] DoD-3: 新增测试全部通过，且不回归现有 Telegram 相关测试。
- [x] DoD-4: `scripts/verify_repo.ps1` 门禁通过，并将结果落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-05 - 小聊回复去机器人口吻（客服化修正）

### Context
- 用户反馈真实会话中 `my_test_bot` 回复“我这边有 xxx 的上下文”，观感明显像机器人而非客服。
- 目标：保留会话记忆能力，同时避免机械模板和原句复读，改为更自然的客服接话方式。

### DoD Mapping (from request)
- [x] DoD-1: 寒暄回复不再使用“我这边有 xxx 上下文”模板。
- [x] DoD-2: 当历史目标是完整请求句时，不再原样复读整句，改为客服化主题标签（如“项目需求”）。
- [x] DoD-3: 增加回归测试，锁定“不复读原句 + 不出现机械模板”行为。
- [x] DoD-4: `scripts/verify_repo.ps1` 通过，且可重启 bot 供用户复测。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-06 - 弱模板模式（只给语境，减少机械话术）

### Context
- 用户要求“能不能只保留必要模板，主要提供语境，让 LLM 自己操作”，目标是降低机器人感。

### DoD Mapping (from request)
- [x] DoD-1: 放宽回复 prompt 的硬模板规则，改为自然对话优先。
- [x] DoD-2: `build_user_reply_payload` 改为极简后处理：仅安全净化 + 必要问题保留，不强加默认推进句/段落模板。
- [x] DoD-3: 保留必要安全约束（内部痕迹过滤、乱码/工程词问题不外露）。
- [x] DoD-4: Telegram 相关回归通过，并通过 `scripts/verify_repo.ps1`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

## Update 2026-03-07 - 客服任务导向回复约束修复（按 MD 流程）

### Queue Binding (this update)
- Queue Item: `ADHOC-20260307-support-task-oriented-dialogue`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- 用户要求按仓库 MD 流程推进，并明确修复“通用助理式续聊”问题。
- 本次目标：把 Telegram 客服回复收敛到“专业客服任务推进”风格，避免空泛续聊、误引用旧项目、无动作输出。

### DoD Mapping (from request)
- [x] DoD-1: 禁止通用安抚+泛问句 fallback，首句必须任务定向。
- [x] DoD-2: 首轮/续轮分流可用；仅在显式续项目时引用历史项目上下文。
- [x] DoD-3: 每轮至少推进一个具体动作（信息请求需带清晰入口选项）。
- [x] DoD-4: 相关回归测试通过，且不回归已有 support/telegram 测试。
- [x] DoD-5: 运行 `scripts/verify_repo.ps1`，记录通过或首个失败点并落盘报告。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [x] `scripts/verify_repo.ps1` passes（或首个失败点已记录）
- [x] `meta/reports/LAST.md` updated in same patch
