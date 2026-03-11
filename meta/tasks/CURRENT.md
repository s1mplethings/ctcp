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

## Update 2026-03-09 - Runtime Wiring / Bridge / Skill Contract Hardening

### Context
- 用户请求：在 `docs/00_CORE.md`、`AGENTS.md`、`ai_context/00_AI_CONTRACT.md` 增补 wiring/integration/skill/error-memory 相关硬规则，并新增统一的 Integration Check 模板。
- 本次范围：docs/meta 合同落盘；不改 `src/ web/ scripts/ tools/ include/` 代码目录。

### DoD Mapping (from request)
- [x] DoD-1: `docs/00_CORE.md` 新增 `0.X Runtime Wiring Contract`、`0.Y Frontend-to-Execution Bridge Rule`、`0.Z Conversation Mode Gate`。
- [x] DoD-2: `AGENTS.md` 新增 `Integration Proof Requirement`、`No Prompt-Only Completion for Wiring Problems`、`Frontend Boundary Rule`。
- [x] DoD-3: `ai_context/00_AI_CONTRACT.md` 新增 Error Memory / User-Facing Failure / Skill Usage / Runtime Skill Consumption 契约。
- [x] DoD-4: 新增模板 `meta/templates/integration_check.md`。
- [x] DoD-5: 落盘本轮任务与报告记录，并执行 `scripts/verify_repo.ps1`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local contract update)`
- [x] Code changes allowed: `N/A (docs/meta only)`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 先按 user 提案将四类契约段落落盘到目标文件。
2) 新建可复用 `integration_check` 模板。
3) 运行唯一验收入口 `scripts/verify_repo.ps1`。
4) 将 Readlist/Plan/Changes/Verify/Questions/Demo 记录到 `meta/reports/LAST.md`。

## Update 2026-03-09 - triplet_integration_guard 专项集成守卫测试

### Context
- 用户请求：新增 `triplet_integration_guard` 专项测试，覆盖 runtime wiring、issue memory accumulation、skill consumption 三类仓库级契约。
- 本次目标：新增 3 个可执行测试文件 + 配套 fixtures，确保“存在于仓库”不再被误判为“已接线/已累积/已消费”。

### DoD Mapping (from request)
- [x] DoD-1: 新增 `tests/test_runtime_wiring_contract.py`，覆盖 greeting 不入项目流水线、详细需求进入项目经理模式、front API 调用桥接路径。
- [x] DoD-2: 新增 `tests/test_issue_memory_accumulation_contract.py`，覆盖用户可见失败捕获、重复失败累积、修复后状态回写。
- [x] DoD-3: 新增 `tests/test_skill_consumption_contract.py`，覆盖“skills 目录存在 != 运行时已消费”、claim 必须有 runtime evidence、未 skillize 必须给理由。
- [x] DoD-4: 新增 `tests/fixtures/triplet_guard/*` 作为 deterministic fixture 集。
- [x] DoD-5: 新增 `meta/reports/triplet_integration_guard.md` 精简报告模板（可选项）。
- [x] DoD-6: 执行新增测试与 `scripts/verify_repo.ps1` 并记录首个失败点。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local contract tests)`
- [x] Code changes allowed: `Yes（tests + fixtures + meta template）`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 新增 `triplet_guard` fixtures（runtime/issue-memory/skill-contract）。
2) 新增 3 个合同测试文件并复用现有 frontend/front-api/_issue_memory 接口。
3) 定向执行新增测试并确保 deterministic pass。
4) 执行 `scripts/verify_repo.ps1`，记录首个失败点与最小修复建议。
5) 回填 `meta/reports/LAST.md`。

## Update 2026-03-09 - Fixed 10-Step Workflow Contract Hardening

### Queue Binding
- Queue Item: `ADHOC-20260309-fixed-10-step-workflow`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 将仓库流程固化为强制 10-step 执行路径，补齐 analysis/find -> plan -> implement -> check/fix -> verify 节奏。
- Scope: `AGENTS.md` / `docs/00_CORE.md` / `ai_context/00_AI_CONTRACT.md` / `ai_context/CTCP_FAST_RULES.md` / `meta/templates/integration_check.md` / `meta/tasks/TEMPLATE.md` / `scripts/workflow_checks.py` / `scripts/verify_repo.ps1` / `scripts/verify_repo.sh` / `docs/03_quality_gates.md`。
- Out of scope: 产品业务逻辑与非流程型功能重构。

## Analysis / Find (before plan)
- Entrypoint analysis: 现有流程入口主要在 `AGENTS.md` 的执行顺序与 `scripts/workflow_checks.py` 的可执行门禁。
- Downstream consumer analysis: `scripts/verify_repo.ps1/.sh` 与 `scripts/plan_check.py` 是流程门禁最终消费端。
- Source of truth: `AGENTS.md`（流程）、`scripts/workflow_checks.py`（前置门禁）、`scripts/verify_repo.*`（最终验收门禁）。
- Current break point / missing wiring: 缺少强制 10-step 顺序、缺少 analysis/find 与 plan-before-implementation 的硬检查、缺少 pre-verify triplet guard gate。
- Repo-local search sufficient: `yes`
- External research artifact: `N/A`

## Integration Check (before implementation)
- upstream: `AGENTS.md` 执行顺序 + `scripts/workflow_checks.py`
- current_module: `scripts/workflow_checks.py`, `scripts/verify_repo.ps1`, `scripts/verify_repo.sh`
- downstream: `scripts/plan_check.py --executed-gates ... --check-evidence` 与 `meta/reports/LAST.md` 审计记录
- source_of_truth: `AGENTS.md` + `scripts/workflow_checks.py` + `scripts/verify_repo.*`
- fallback: 若 triplet guard 暂不适合集成 verify_repo，则保留在 step8 本地循环并在 `LAST.md` 明确 gap（本次已直接接入 verify_repo）
- acceptance_test: `python scripts/workflow_checks.py` + triplet 3 测 + `scripts/verify_repo.ps1`
- forbidden_bypass: 跳过 analysis/find、跳过 plan、跳过 check/fix loop、仅改 prompt 处理 wiring 问题
- user_visible_effect: 未来变更流程必须先分析与计划，再进入实现并循环修复；无法再“读文档后直接改代码然后一次 verify”。

## DoD Mapping (from request)
- [x] DoD-1: `AGENTS.md` 执行顺序重构为固定 10-step。
- [x] DoD-2: `docs/00_CORE.md` 增加固定 10-step 原则（简洁硬规则）。
- [x] DoD-3: `ai_context/00_AI_CONTRACT.md` 增补 10-step 与 connected/accumulated/consumed 完成证明。
- [x] DoD-4: `meta/templates/integration_check.md` 增补 `acceptance_test` 与 `user_visible_effect`。
- [x] DoD-5: `meta/tasks/TEMPLATE.md` 强化 analysis/find + integration check + fix loop + completion criteria。
- [x] DoD-6: `scripts/workflow_checks.py` 增加 10-step 关键证据字段门禁。
- [x] DoD-7: `scripts/verify_repo.ps1/.sh` 接入 triplet guard gate。
- [x] DoD-8: `docs/03_quality_gates.md` 与脚本门禁顺序同步。

## Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local workflow hardening)`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Analysis/find contract drift and gate coverage gaps.
2) Update contracts/docs/templates to fixed 10-step flow.
3) Implement executable gate checks in `scripts/workflow_checks.py`.
4) Add triplet guard gate to `scripts/verify_repo.ps1/.sh`.
5) Run local check / contrast / fix loop:
   - `python scripts/workflow_checks.py`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
6) Run canonical verify gate: `scripts/verify_repo.ps1`.
7) Completion criteria: prove connected + accumulated + consumed.

## Notes / Decisions
- Default choices made: 将 triplet guard 直接接入 verify_repo，作为 canonical gate 的硬子步骤。
- Alternatives considered: 仅在 AGENTS 文档声明 step8 不改 verify_repo；已拒绝（可跳过风险高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为流程固化改动，无新增用户可见失败缺陷条目；保持“若触发则必须记录”规则。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository workflow hardening, not a reusable runtime feature workflow.

## Update 2026-03-09 - Single-Purpose/Single-Flow Operating Model Refactor

### Queue Binding
- Queue Item: `ADHOC-20260309-single-purpose-single-flow-model`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 将仓库重构为单一目的、单一主流程、单一职责分层、单一关注点真相源。
- Scope: contracts/docs/templates/workflow gate 强化；不改业务功能逻辑。
- Out of scope: 产品功能行为扩展与运行时算法重写。

## Task Truth Source (single source for current task)
- task_purpose: 固化 repo purpose / canonical flow / current task scope / runtime truth 的单一来源。
- allowed_behavior_change: 文档契约重构、模板字段扩展、workflow gate 检查强化、verify/docs 索引同步。
- forbidden_goal_shift: 不得将任务扩展为产品需求重设计或前后端新功能开发。
- in_scope_modules: `docs/01_north_star.md`, `docs/04_execution_flow.md`, `docs/05_agent_mode_matrix.md`, `AGENTS.md`, `docs/00_CORE.md`, `docs/00_overview.md`, `docs/02_workflow.md`, `docs/10_workflow.md`, `docs/10_team_mode.md`, `docs/adlc_pipeline.md`, `docs/22_teamnet_adlc.md`, `meta/tasks/TEMPLATE.md`, `scripts/workflow_checks.py`, `scripts/sync_doc_links.py`, `README.md`, `docs/25_project_plan.md`, `ai_context/00_AI_CONTRACT.md`.
- out_of_scope_modules: `src/`, `frontend/` 业务实现逻辑、`scripts/ctcp_orchestrate.py` 运行态算法。
- completion_evidence: workflow checks + triplet guard + canonical verify 结果 + LAST 报告证据。

## Analysis / Find (before plan)
- Entrypoint analysis: agent 行为入口受 `AGENTS.md` 与 `docs/04_execution_flow.md` 约束。
- Downstream consumer analysis: `scripts/workflow_checks.py` 与 `scripts/verify_repo.*` 是执行层硬门禁消费端。
- Source of truth: repo purpose=`docs/01_north_star.md`; flow=`docs/04_execution_flow.md`; current task=`meta/tasks/CURRENT.md`; runtime truth=`docs/00_CORE.md`。
- Current break point / missing wiring: 多文档重复定义 purpose/flow，CURRENT 缺少显式 task truth 字段，容易中途 goal drift。
- Repo-local search sufficient: `yes`
- External research artifact: `N/A`

## Integration Check (before implementation)
- upstream: `AGENTS.md` preflight + canonical flow references
- current_module: `docs/01_north_star.md`, `docs/04_execution_flow.md`, `scripts/workflow_checks.py`
- downstream: `scripts/verify_repo.ps1/.sh` + `meta/reports/LAST.md`
- source_of_truth: `docs/01_north_star.md` / `docs/04_execution_flow.md` / `meta/tasks/CURRENT.md` / `docs/00_CORE.md`
- fallback: 若历史文档仍需保留，仅允许降级为 lane/subsystem 文档并显式声明非 canonical
- acceptance_test: `python scripts/workflow_checks.py` + triplet tests + `scripts/sync_doc_links.py --check` + `scripts/verify_repo.ps1`
- forbidden_bypass: 跳过 task truth 字段、在 AGENTS/README 静默改目的、只改 prompt 不改门禁
- user_visible_effect: 未来 agent 更容易识别唯一目的/流程/任务边界，减少实现中途改目标。

## DoD Mapping (from request)
- [x] DoD-1: 新增单一 repo purpose 文档 `docs/01_north_star.md`。
- [x] DoD-2: 新增单一 canonical flow 文档 `docs/04_execution_flow.md`。
- [x] DoD-3: 新增 mode/responsibility 矩阵 `docs/05_agent_mode_matrix.md`。
- [x] DoD-4: 收敛旧 overview/workflow 文档为 lane/scope 文档并标注非 canonical。
- [x] DoD-5: `AGENTS.md` 增加三重识别和冲突停机规则。
- [x] DoD-6: `meta/tasks/TEMPLATE.md` 与 workflow gate 增加 task truth 字段。
- [x] DoD-7: 明确 runtime truth 只来自 run artifacts + verify outputs + explicit reports。

## Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local contract refactor)`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Create single-purpose/single-flow/single-mode authoritative docs.
2) Reclassify overlapping overview/workflow docs and README source map.
3) Strengthen AGENTS role to operating rules + conflict stop path.
4) Strengthen task template and workflow gate for current-task truth fields.
5) Run check/contrast/fix loop:
   - `python scripts/workflow_checks.py`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
6) Run canonical verify gate: `scripts/verify_repo.ps1`.
7) Completion criteria: prove connected + accumulated + consumed.

## Notes / Decisions
- Default choices made: 保留历史文档但收敛为 lane/scope，不做破坏式删除。
- Alternatives considered: 直接删除旧 workflow/overview 文档；已拒绝（迁移风险过高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为流程契约重构，未触发新的用户可见失败条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository governance refactor rather than a reusable runtime workflow feature.

## Update 2026-03-09 - Scaffold Live-Reference Dual Source Mode (CTCP project generation chain)

### Queue Binding
- Queue Item: `ADHOC-20260309-scaffold-live-reference-mode`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 升级 `scaffold` / `scaffold-pointcloud` 为双模式（`template` + `live-reference`），将 CTCP 母仓库受控导出接入项目生成链与后续 verify/执行链。
- Scope: doc-first 同步文档 + 新增受控导出清单/导出 helper + orchestrate 编排扩展 + 测试补齐 + 验收。
- Out of scope: `new-run/advance/cos-user-v2p` 核心语义重构；provider/manual_outbox 流程重构；整仓镜像导出。

## Task Truth Source (single source for current task)

- task_purpose: 为 CTCP 项目生成链新增 `live-reference` 模式，在不破坏现有模板模式前提下实现白名单受控导出与来源审计。
- allowed_behavior_change:
  - `scaffold`/`scaffold-pointcloud` CLI 新增 `--source-mode` 并在 `live-reference` 分支执行受控导出。
  - 新增 `meta/reference_export_manifest.yaml` 与导出逻辑、来源元数据与报告字段。
  - 扩展项目 manifest 字段与 run_dir 证据字段。
  - 新增/更新相关测试与文档。
- forbidden_goal_shift:
  - 不得改成整仓复制导出。
  - 不得删除现有 template 模式或破坏默认行为。
  - 不得扩大到无关模块重构。
- in_scope_modules:
  - `meta/reference_export_manifest.yaml`
  - `tools/reference_export.py`
  - `scripts/ctcp_orchestrate.py`
  - `README.md`
  - `docs/40_reference_project.md`
  - `docs/30_artifact_contracts.md`
  - `tests/test_scaffold_reference_project.py`
  - `tests/test_scaffold_pointcloud_project.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `src/`, `frontend/` 业务实现、provider 路由链、`scripts/ctcp_dispatch.py`、`scripts/ctcp_front_api.py`。
- completion_evidence:
  - scaffold/template 回归通过；
  - scaffold-pointcloud/template 回归通过；
  - live-reference 新增路径测试通过；
  - `scripts/verify_repo.ps1` 结果记录（PASS 或首个失败点+最小修复）。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_orchestrate.py` 的 `cmd_scaffold` 与 `cmd_scaffold_pointcloud` 为唯一生成入口。
- Downstream consumer analysis:
  - 生成输出由 `cos-user-v2p`、项目内 `scripts/verify_repo.ps1`、后续 CTCP 执行链消费。
  - run_dir 证据由 `TRACE.md`、`events.jsonl`、`artifacts/*report.json` 消费。
- Source of truth:
  - 导出白名单真源：`meta/reference_export_manifest.yaml`。
  - 当前任务范围真源：本文件（`meta/tasks/CURRENT.md`）。
  - 运行契约真源：`docs/00_CORE.md` + verify gate。
- Current break point / missing wiring:
  - 现有 scaffold 仅模板模式，无 live-reference 导出与来源追踪。
  - pointcloud `--force` 当前不是 manifest-only 清理。
  - 缺少 `reference_source.json` 与 source-mode/source-commit 证据字段。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `python scripts/ctcp_orchestrate.py scaffold|scaffold-pointcloud ... --source-mode ...`
- current_module: `scripts/ctcp_orchestrate.py` + `tools/reference_export.py`
- downstream: 生成项目内 `meta/manifest.json`/`manifest.json` + `meta/reference_source.json` + run_dir `scaffold*_report.json`
- source_of_truth: `meta/reference_export_manifest.yaml`（唯一导出白名单）
- fallback: git commit 获取失败时写 `unknown`；非法清单/越界路径/危险清理直接 fail 并写报告错误
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v`
  - `python -m unittest discover -s tests -p "test_scaffold_pointcloud_project.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 通过“遍历全仓+黑名单”导出
  - 直接整仓复制（除 `.git` 外全拷）
  - `--force` 删除 manifest 之外未知文件
  - 路径穿越/导出到 repo 内
- user_visible_effect:
  - 用户可显式选择 `template` 或 `live-reference`。
  - live-reference 生成结果含来源 commit、source mode、导出清单与继承统计，可继续执行 verify/cos-user/new-run/advance 链路。

## DoD Mapping (from request)
- [ ] DoD-1: scaffold/scaffold-pointcloud 新增 `--source-mode template|live-reference`，默认 `template`。
- [ ] DoD-2: 新增受版本控制导出清单并作为 live-reference 唯一白名单来源。
- [ ] DoD-3: live-reference 仅按白名单导出，具备路径安全校验与来源 commit 回填。
- [ ] DoD-4: 生成 `meta/reference_source.json`，扩展 manifest/source 字段与 run_dir 报告字段。
- [ ] DoD-5: pointcloud 保持 template 模式兼容，live-reference 可继承 CTCP 规范 + pointcloud 项目文件。
- [ ] DoD-6: 文档与测试同步，verify 结果落盘。

## Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [ ] `scripts/verify_repo.*` passes（待本轮执行后回填）
- [ ] `meta/reports/LAST.md` updated in same patch（进行中）

## Plan
1) 先落盘本轮任务与报告计划（bind/read/analyze/integration）。
2) 新增导出清单与导出 helper（白名单、路径校验、copy/transform、exclude/required、source commit）。
3) 改 `ctcp_orchestrate`：接入 source-mode、live-reference 编排、manifest/reference_source/report 字段、manifest-only force 清理。
4) doc-first 更新 `README.md` 与 `docs/40_reference_project.md`，并补 `docs/30_artifact_contracts.md` 新契约字段。
5) 补测试：template 回归 + live-reference 成功路径 + 白名单 + token + 安全边界 + source commit fallback。
6) 执行本地回归 + canonical verify，将结果回填到 `meta/reports/LAST.md`。

## Notes / Decisions
- Default choices made: live-reference 默认导出清单路径为 `meta/reference_export_manifest.yaml`；source commit 获取失败回填 `unknown`。
- Alternatives considered: 直接复用 templates 全量复制；已拒绝（不满足 live-reference 受控导出目标）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为功能扩展，若出现用户可见导出失败将通过新增回归测试固化。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository-specific scaffold generation wiring change, not a reusable runtime workflow asset.

## Results (2026-03-09 - Scaffold live-reference dual-mode)

- Files changed:
  - `meta/reference_export_manifest.yaml`
  - `meta/templates/reference_tokens.md`
  - `tools/reference_export.py`
  - `tools/scaffold.py`
  - `scripts/ctcp_orchestrate.py`
  - `README.md`
  - `docs/40_reference_project.md`
  - `docs/30_artifact_contracts.md`
  - `tests/test_scaffold_reference_project.py`
  - `tests/test_scaffold_pointcloud_project.py`
  - `tests/fixtures/reference_export/bad_traversal_source_manifest.yaml`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- DoD completion status:
  - [x] DoD-1: scaffold/scaffold-pointcloud 新增 `--source-mode` 且默认 `template`
  - [x] DoD-2: 新增 `meta/reference_export_manifest.yaml` 作为 live-reference 白名单真源
  - [x] DoD-3: live-reference 导出白名单+路径安全+source commit fallback
  - [x] DoD-4: 生成 `meta/reference_source.json` 并扩展 manifest/report 字段
  - [x] DoD-5: pointcloud template 模式保持回归，live-reference 可生成 CTCP-style 关键输出
  - [ ] DoD-6: canonical verify 全量通过（当前首个失败仍在 lite replay S16，见 `meta/reports/LAST.md`）

- Verification summary:
  - scaffold/scaffold-pointcloud + triplet guard 定向测试通过。
  - `scripts/verify_repo.ps1` 首个失败点：`lite scenario replay / S16_lite_fixer_loop_pass`。

- Queue status update suggestion (`todo/doing/done/blocked`): `blocked` (blocked by pre-existing lite replay S16 fixture convergence on current dirty baseline).

## Update 2026-03-09 - Frontend control plane + single execution bridge (Phase 1-2)

### Queue Binding
- Queue Item: `ADHOC-20260309-frontend-control-plane-single-bridge`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 在 CTCP 执行核心之上实现 text-first 的“类人项目经理”前端控制平面，并强制单桥执行接入。
- Scope: `frontend/*` 路由/提取/问答/脱敏流水线 + `tools/telegram_cs_bot.py` 与 `scripts/ctcp_front_bridge.py` 的执行桥接线路强化 + 对应测试。
- Out of scope: 真实语音流式 runtime、avatar/VTuber 呈现层、CTCP orchestrator 内核策略重写。

## Task Truth Source (single source for current task)

- task_purpose: 将客服/前端行为稳定为 text-first PM 控制平面，并把所有执行相关调用收敛到单一 CTCP bridge。
- allowed_behavior_change:
  - 强化 frontend conversation mode routing / requirement extraction / known-info gating / high-leverage question 选择。
  - 强化用户可见回复五阶段流水线（extract -> draft -> review -> sanitize -> final）。
  - 将 `tools/telegram_cs_bot.py` 的 new-run/status/advance/decision/upload/report 相关执行路径收敛到 `scripts/ctcp_front_bridge.py`。
  - 增补桥接与前端边界测试。
- forbidden_goal_shift:
  - 不得把工程执行逻辑迁入 frontend。
  - 不得引入并行 hidden execution path 绕开 bridge。
  - 不得扩展到实时语音/多模态完整实现。
- in_scope_modules:
  - `frontend/conversation_mode_router.py`
  - `frontend/project_manager_mode.py`
  - `frontend/response_composer.py`
  - `frontend/message_sanitizer.py`
  - `tools/telegram_cs_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/reports/LAST.md`
  - `meta/tasks/CURRENT.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py` 执行状态机语义
  - `src/` / `include/` C++ 执行核心
  - 实时音视频 transport 与中断处理运行时
- completion_evidence:
  - 前端边界测试通过（greeting/detail/dedupe/leakage/state consistency）
  - bridge 路径测试通过（create/status/advance/decision/upload）
  - triplet guard + canonical verify 结果已记录

## Analysis / Find (before plan)

- Entrypoint analysis:
  - 文本客服主入口：`tools/telegram_cs_bot.py`
  - 支持链路入口：`scripts/ctcp_support_bot.py`
  - bridge 入口：`scripts/ctcp_front_bridge.py`、`scripts/ctcp_front_api.py`
- Downstream consumer analysis:
  - 用户侧可见输出由 `frontend/response_composer.py` 最终闸门消费。
  - 执行状态与变更由 CTCP run artifacts（`RUN.json`/`verify_report.json`/`outbox`）和 bridge 事件消费。
- Source of truth:
  - 工程执行真源：CTCP run_dir artifacts + `scripts/verify_repo.ps1` 结果。
  - 前端会话决策真源：frontend pipeline state + support session state（仅会话，不可替代执行真源）。
- Current break point / missing wiring:
  - `tools/telegram_cs_bot.py` 当前含 `_run_orchestrate` 直接子进程调用与 target-path 直写，存在 bridge bypass 风险。
  - conversation mode / requirement / sanitizer 已有实现，但需与单桥执行路径做集成证明与回归覆盖。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram/customer 文本消息入口 `tools/telegram_cs_bot.py` 与 frontend render pipeline 调用点。
- current_module: `tools/telegram_cs_bot.py` bridge adapter + `frontend/response_composer.py` 多阶段控制平面。
- downstream: `scripts/ctcp_front_bridge.py`（ctcp_new_run/ctcp_get_status/ctcp_advance/ctcp_list_decisions_needed/ctcp_submit_decision/ctcp_upload_artifact/ctcp_get_last_report）-> CTCP run artifacts。
- source_of_truth: CTCP run_dir 状态与 `verify_report.json`；frontend 仅做可见层编排与脱敏。
- fallback: bridge 异常时仅给用户自然降级说明，不暴露内部错误细节；执行不由前端直连替代。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 前端直接写 run artifact target path 作为常规路径
  - 前端直接调用 `ctcp_orchestrate.py` 进行 new-run/advance/status 作为主路径
  - 用户可见回复中泄漏 provider/log/rc/internal prompt
- user_visible_effect:
  - 寒暄不再误触发项目规划
  - 详细需求可直接进入 PM 口径摘要与 1-2 个关键问题
  - 执行动作稳定走单桥，用户侧看到一致、自然、无内部泄漏的短文本回复

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: frontend text control plane routes greeting and smalltalk away from project planning while preserving PM-style project handling.
- [ ] DoD-2: frontend execution mutations and run-state queries go through scripts/ctcp_front_bridge.py bridge capabilities only.
- [ ] DoD-3: tests cover greeting isolation, detailed requirement understanding, duplicate-question prevention, leakage guard, single-bridge invocation path, and non-contradictory visible state.

## Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local frontend/bridge refactor)`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 先保持 doc/spec-first：绑定 queue + CURRENT 记录三重识别、task truth、integration check。
2) 收敛前端执行入口：在 `tools/telegram_cs_bot.py` 通过 `ctcp_front_bridge` 适配器替换 direct orchestrate/new-run/advance/status 及 decision/upload 路径。
3) 保持并补强 text-first PM 控制平面：router/extractor/known-info/question/sanitizer/final gate 行为维持一致并修复边界缺口。
4) 增补测试覆盖“单桥 enforcement + 前端可见行为稳定性”并执行本地 check/fix loop。
5) 运行 triplet guard 与 canonical verify，记录首个失败点和最小修复策略。
6) Completion criteria: prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made: 复用既有 frontend 模块，不新建并行执行逻辑；仅在 `telegram_cs_bot` 执行相关路径做 bridge 收敛。
- Alternatives considered: 全量重写 support bot 架构；已拒绝（超出 Phase 1-2 范围且回归风险高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 如发现用户可见泄漏/路由误触发回归，按 triplet issue-memory contract 更新回归条目与状态。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch is repository-local integration wiring and does not introduce a stable reusable runtime workflow asset yet.

## Results (2026-03-09 - Frontend control plane + single bridge)

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `tools/telegram_cs_bot.py`
  - `tests/test_runtime_wiring_contract.py`

- DoD completion status:
  - [x] DoD-1: greeting/smalltalk 与项目路由隔离，PM 风格项目回复保持。
  - [x] DoD-2: frontend 执行相关路径改为 bridge（new-run/status/advance/list decisions/submit decision/upload/report）。
  - [x] DoD-3: 覆盖 greeting isolation / detailed requirement / dedupe / leakage / single-bridge / one-visible-state 的回归测试通过。

- Acceptance status:
  - [x] DoD written (this file complete)
  - [x] Research logged (if needed): `N/A (repo-local frontend/bridge refactor)`
  - [x] Code changes allowed
  - [x] Patch applies cleanly (`git diff` generated, no destructive operations used)
  - [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
  - [x] Demo report updated: `meta/reports/LAST.md`

- Verification summary:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (15 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (20 passed)
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (22 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure gate: `lite scenario replay`
    - first failed scenario: `S16_lite_fixer_loop_pass`
    - failure detail: `step 6: expect_exit mismatch, rc=1, expect=0`
    - evidence:
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/summary.json`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/S16_lite_fixer_loop_pass/TRACE.md`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260309-225449/S16_lite_fixer_loop_pass/sandbox/20260309-225622-687595-orchestrate/artifacts/verify_report.json`
    - minimal repair strategy:
      - 更新 `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` 对应的预期输出样本，使其匹配当前 frontend 文本口径（`B01-B06/U26` reply assertions）。
      - 保持修复范围仅限 simlab fixture 与对应断言，不扩展到运行时业务逻辑。

- Queue status update suggestion (`todo/doing/done/blocked`): `blocked` (blocked by pre-existing simlab S16 fixture drift on current baseline).

## Update 2026-03-10 - Markdown 对象状态机治理基线（6-file baseline）

### Queue Binding
- Queue Item: `ADHOC-20260310-md-object-state-machine`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- 用户目标：把 markdown 体系从“说明书集合”升级为“对象 + 状态机管理”，防止旧流程被直接删掉和废弃对象暗中继续生效。
- 本次范围：先落地最小可用基线（registry + state machine + process/rule/strategy 三个 active 对象），不做运行时代码行为改造。
- Out of scope:
  - orchestrator/runtime 逻辑变更
  - frontend/support 链路行为改动
  - 全量历史文档一次性迁移

## Task Truth Source (single source for current task)

- task_purpose: 建立 markdown 对象状态管理基线，形成可审计的对象状态真源与转移规则。
- allowed_behavior_change:
  - 新增 `docs/10_REGISTRY.md` 与 `docs/20_STATE_MACHINE.md`。
  - 新增对象化文档：`PROC-main-workflow`、`RULE-no-direct-delete`、`STRAT-inheritance-check`。
  - 在 `docs/00_CORE.md` 增加 markdown 对象生命周期契约入口。
- forbidden_goal_shift:
  - 不得改写仓库 North Star 与 canonical 10-step 执行语义。
  - 不得把 docs 改造扩展为运行时执行重构任务。
  - 不得静默删除现有历史文档。
- in_scope_modules:
  - `docs/00_CORE.md`
  - `docs/10_REGISTRY.md`
  - `docs/20_STATE_MACHINE.md`
  - `docs/processes/PROC-main-workflow.md`
  - `docs/rules/RULE-no-direct-delete.md`
  - `docs/strategies/STRAT-inheritance-check.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `frontend/*`
  - `tools/telegram_cs_bot.py`
  - `src/` 和 `include/` 运行时代码
- completion_evidence:
  - 新增对象状态文档存在且互相引用一致。
  - triplet guard tests 通过。
  - canonical verify 已执行并记录结果（PASS 或首个失败点 + 最小修复策略）。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - docs 治理入口来自 `docs/00_CORE.md` + `meta/tasks/CURRENT.md` task truth + queue 绑定。
- Downstream consumer analysis:
  - 规划/实施 agent 在改流程类文档前应先读取 registry/state-machine。
  - verify/workflow gate 消费 `meta/tasks/CURRENT.md` 与 `meta/reports/LAST.md` 证据链。
- Source of truth:
  - 对象当前状态真源：`docs/10_REGISTRY.md`。
  - 状态转移真源：`docs/20_STATE_MACHINE.md`。
  - 任务范围真源：本文件当前 update 段。
- Current break point / missing wiring:
  - 现状缺少对象状态真源，流程文档可被整体覆盖且难以追踪替代关系。
  - 缺少“禁止直接删除”硬规则与继承检查策略对象。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `docs/00_CORE.md` contract reader + task binding (`meta/tasks/CURRENT.md`).
- current_module: `docs/10_REGISTRY.md` + `docs/20_STATE_MACHINE.md` + object docs (`processes/strategies/rules`).
- downstream: docs governance decisions, future process updates, and verify evidence records in `meta/reports/LAST.md`.
- source_of_truth: `docs/10_REGISTRY.md` (object state) and `docs/20_STATE_MACHINE.md` (transition legality).
- fallback: transition preconditions missing时阻断状态推进，保持原状态并要求补齐决策/证据。
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 跳过 registry 直接宣布对象状态变更。
  - 直接 `active -> removed` 或 `active -> archived`。
  - 仅在 chat/prompt 声明废弃，不更新 registry/decision/evidence。
- user_visible_effect:
  - 文档治理改为对象状态驱动；当前正式对象一眼可查。
  - 旧流程不可再被一步删除，必须经过可审计迁移阶段。

## DoD Mapping (from request)

- [x] DoD-1: 引入状态机核心文档（registry + state machine）并定义统一状态集合。
- [x] DoD-2: 建立最小 active 对象集（process/strategy/rule）并使用唯一 ID。
- [x] DoD-3: 明确“禁止直接删除”与“继承检查”策略作为正式对象。
- [ ] DoD-4: 完成 check/fix loop + canonical verify 并记录结果。

## Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed (`docs/meta only`)
- [x] Doc/spec-first change included in same patch
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] `meta/reports/LAST.md` updated in same patch

## Plan

1) 绑定 ADHOC queue，并在 CURRENT 写入 task truth + integration check。
2) 落地 6-file baseline（registry/state machine/process/rule/strategy + core 链接入口）。
3) 执行 docs 相关 check 与 triplet guard 本地回归。
4) 运行 canonical verify 并记录首个失败点或通过结果。
5) 回填 `meta/reports/LAST.md` 与本文件 results，给出 `connected + accumulated + consumed` 证据。

## Notes / Decisions

- Default choices made: 先实施最小对象集合，不做一次性历史清理。
- Alternatives considered: 直接全量重构所有 docs 为对象化；已拒绝（改动面过大，风险高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为 docs governance 基线建设，未观察到新的用户可见运行时故障，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch defines repository-local governance baseline docs rather than a reusable runtime workflow asset.

## Results (2026-03-10 - Markdown object state machine baseline)

- Files changed:
  - `docs/00_CORE.md`
  - `docs/10_REGISTRY.md`
  - `docs/20_STATE_MACHINE.md`
  - `docs/processes/PROC-main-workflow.md`
  - `docs/rules/RULE-no-direct-delete.md`
  - `docs/strategies/STRAT-inheritance-check.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- DoD completion status:
  - [x] DoD-1: 状态机核心文档与状态集合落地。
  - [x] DoD-2: 最小 active 对象集落地并登记。
  - [x] DoD-3: no-direct-delete + inheritance-check 作为正式对象落地。
  - [ ] DoD-4: canonical verify 全量通过（当前首个失败为 lite replay S16）。

- Acceptance status:
  - [x] DoD written
  - [x] Code changes allowed (`docs/meta only`)
  - [x] Doc/spec-first change included in same patch
  - [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
  - [x] `meta/reports/LAST.md` updated in same patch

- Verification summary:
  - `python scripts/workflow_checks.py` => `0` (`[workflow_checks] ok`)
  - `python scripts/sync_doc_links.py --check` => `0` (`[sync_doc_links] ok`)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure gate: `lite scenario replay`
    - first failed scenario: `S16_lite_fixer_loop_pass`
    - failure detail: `step 6: expect_exit mismatch, rc=1, expect=0`
    - evidence:
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-005420/summary.json`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-005420/S16_lite_fixer_loop_pass/TRACE.md`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260310-005420/S16_lite_fixer_loop_pass/sandbox/20260310-005550-884425-orchestrate/artifacts/verify_report.json`
    - minimal repair strategy:
      - 更新 S16 fixer fixture 使其在 replay 沙箱内满足最新 `workflow_checks` 规则（补齐 `meta/tasks/CURRENT.md` docs/spec-first update 证据），避免第二轮 advance 再次触发 verify FAIL。
      - 保持修复范围在 simlab fixture/expectation，不扩展业务运行时代码。

- Queue status update suggestion (`todo/doing/done/blocked`): `blocked` (blocked by existing lite replay S16 fixture drift).

## Update 2026-03-10 - 客服与项目设计流程接线（librarian + 白板）

### Queue Binding
- Queue Item: `ADHOC-20260310-support-project-whiteboard-librarian`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`（adhoc 追加）

### Context
- Goal: 把客服会话与项目设计流程接线，通过 librarian 检索与白板记录形成“提问-检索-回问-继续推进”的单轮闭环。
- Scope:
  - `tools/telegram_cs_bot.py` 增加 support whiteboard 状态工件与 librarian 接线。
  - 用户可见回复维持单条主回复，白板/检索摘要并入主回复，不拆多条。
  - 旧会话清理/新目标 hard reset 时同步清理 whiteboard 工件。
  - 增补最小回归测试覆盖白板接线与清理行为。
- Out of scope:
  - orchestrator 状态机语义变更
  - CTCP planner/chair/librarian 主流程协议重构
  - 新依赖引入

### Task Truth Source (single source for current task)

- task_purpose: 让客服通道能够和项目设计流程共享“白板 + librarian”检索上下文，并保持单一用户可见输出。
- allowed_behavior_change:
  - 新增 `artifacts/support_whiteboard.json` / `artifacts/support_whiteboard.md` 的会话级白板记录。
  - 在 support turn 中接入 `tools.local_librarian.search`（可选/容错），把检索结果写入白板并生成自然客服摘要。
  - 在 `_build_support_reply_prompt` 注入 whiteboard snapshot，供 reply provider 读取。
  - 扩展清理路径，删除旧会话时同时清掉 whiteboard 工件。
  - 测试覆盖白板接线与清理。
- forbidden_goal_shift:
  - 不得把 frontend/support 变成并行执行引擎，执行修改仍走 bridge。
  - 不得向用户泄露内部路径/工件名（analysis/outbox/run_dir 等）。
  - 不得恢复 archive-first 清理行为。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `frontend/response_composer.py`（本轮无行为改动）
  - `src/` / `include/`
- completion_evidence:
  - support turn 可写入 whiteboard + librarian 检索条目。
  - 用户回复保持单条主回复并包含白板协作摘要。
  - cleanup/new-goal hard reset 后 whiteboard 工件被清理。
  - 相关单测通过。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户入口：`Bot._handle_message -> _handle_support_turn`。
- Downstream consumer analysis:
  - 用户可见输出：`_send_customer_reply` 单一公开闸门。
  - provider 输入：`_build_support_reply_prompt`。
- Source of truth:
  - 会话真源：`artifacts/support_session_state.json`
  - 白板真源：`artifacts/support_whiteboard.json`
- Current break point / missing wiring:
  - 原有链路缺少“客服 <-> 项目设计”共享白板与 librarian 互问互查。
  - 清理旧会话时未覆盖白板工件（新增后需同步清理）。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: Telegram text turn (`tools/telegram_cs_bot.py::_handle_message`).
- current_module: `Bot._support_librarian_whiteboard_exchange` + whiteboard load/save helpers.
- downstream: `_send_customer_reply`（用户侧）与 `_build_support_reply_prompt`（provider 侧 whiteboard snapshot）。
- source_of_truth: `artifacts/support_whiteboard.json`（白板）+ `artifacts/support_session_state.json`（会话）。
- fallback: `local_librarian` 不可用或检索异常时，仅记录白板提问并继续客服回复，不阻断主流程。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
- forbidden_bypass:
  - 直接多条 send 绕过 `_send_customer_reply` 主闸门。
  - 仅在 prompt 文本中宣称白板协同但不落盘工件。
  - 清理路径遗漏 whiteboard 导致旧状态残留。
- user_visible_effect:
  - 用户能在同一条回复中感知“已写入白板 + 已检索线索 + 下一步问题”。
  - 删除旧会话后旧白板记录不再污染新项目。

### DoD Mapping (from request)

- [x] DoD-1: support turn 增加 librarian + whiteboard 协同接线并落盘。
- [x] DoD-2: 用户可见输出保持单条主回复（白板摘要并入，不拆多条）。
- [x] DoD-3: reply provider prompt 可读取 whiteboard snapshot。
- [x] DoD-4: cleanup/new-goal reset 同步清理 whiteboard 工件。
- [x] DoD-5: 最小回归测试覆盖白板接线与清理行为。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [ ] `scripts/verify_repo.*` full pass（本轮仅执行 targeted test set）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 在 `telegram_cs_bot` 增加 whiteboard state load/save 与 snapshot。
2) 在 support turn 加入 librarian 检索 + 白板写入 + 单条回复并入策略。
3) 在 provider prompt 注入 whiteboard snapshot。
4) 扩展 purge/reset 路径清理 whiteboard 工件。
5) 增补并执行回归测试，记录结果。

### Notes / Decisions

- Default choices made: 采用 repo-local `tools.local_librarian.search`；不引入新依赖。
- Alternatives considered: 新建独立 whiteboard service；拒绝（超出最小改动范围）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本轮未观察新的用户可见泄漏/回归，暂不新增 issue_memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch is repository-local integration wiring and not a stable reusable skill asset yet.

### Results (2026-03-10 - support/project whiteboard+librarian loop)

- Files changed:
  - `tools/telegram_cs_bot.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (29 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (20 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (17 passed)
  - `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py` => `0`

- Queue status update suggestion (`todo/doing/done/blocked`): `done` (targeted wiring + regression coverage complete).

## Update 2026-03-10 - 客服+生产Agent共享白板与Librarian协同

### Queue Binding
- Queue Item: `ADHOC-20260310-support-production-librarian-whiteboard`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 让客服与所有生产执行 agent 在同一 whiteboard 上共享 librarian 检索线索，形成“支持侧提问 -> 生产侧执行 -> 结果回写”的闭环协作。
- Scope:
  - 在 dispatch 链路增加白板读写与 librarian 线索注入。
  - 把白板快照注入生产 provider prompt（manual_outbox + api_agent）。
  - 与现有 `support_whiteboard` 工件复用，避免 support/production 上下文分裂。
  - 增加最小回归测试覆盖 dispatch 白板接线和 prompt 注入。
- Out of scope:
  - orchestrator 状态机语义变更。
  - frontend bridge 能力扩展。
  - 新外部依赖引入。

### Task Truth Source (single source for current task)

- task_purpose: 把生产 agent（chair/librarian/guardian/cost_controller/researcher/patchmaker/fixer）的派发执行接线到共享 whiteboard + librarian 协同上下文，并与客服通道共用同一白板真源。
- allowed_behavior_change:
  - `scripts/ctcp_dispatch.py` 增加 shared whiteboard state 读写、librarian 查询和 request 注入。
  - `tools/providers/manual_outbox.py` 与 `tools/providers/api_agent.py` prompt 注入 whiteboard snapshot 与 librarian hits。
  - 使用 `artifacts/support_whiteboard.json` 作为 shared whiteboard truth source（生产侧与客服侧共用）。
  - 增补 `tests/test_provider_selection.py`、`tests/test_api_agent_templates.py` 回归用例。
- forbidden_goal_shift:
  - 不得绕过 dispatch/provider 主链路新增并行执行路径。
  - 不得改变 verify 入口或 gate 语义。
  - 不得向用户回复泄露内部路径/日志细节。
- in_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/manual_outbox.py`
  - `tools/providers/api_agent.py`
  - `tests/test_provider_selection.py`
  - `tests/test_api_agent_templates.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `frontend/*`
  - `src/` / `include/`
  - `tools/telegram_cs_bot.py`（本轮仅复用其 whiteboard 工件）
- completion_evidence:
  - dispatch 执行后在 run_dir 写入共享 whiteboard 条目（agent request + librarian hit + execution result）。
  - manual_outbox/api_agent prompt 含 whiteboard snapshot。
  - targeted tests + triplet guard 通过，canonical verify 执行并记录结果。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 生产链路入口是 `scripts/ctcp_dispatch.py::dispatch_once`，由 orchestrator blocked/fail gate 触发。
- Downstream consumer analysis:
  - `manual_outbox` / `api_agent` 读取 request 并生成目标 artifact；后续由 orchestrator 消费产物推进状态机。
- Source of truth:
  - 共享白板真源为 `${run_dir}/artifacts/support_whiteboard.json`。
  - librarian 检索来自 repo-local `tools.local_librarian.search`。
- Current break point / missing wiring:
  - 现有白板+librarian 只在客服 support turn，生产 dispatch 没有接线，导致支持侧与执行侧上下文断开。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: orchestrator dispatch trigger -> `ctcp_dispatch.dispatch_once`.
- current_module: shared whiteboard helpers in `ctcp_dispatch` + provider prompt rendering in `manual_outbox`/`api_agent`.
- downstream: provider prompt consumption -> target artifact generation -> orchestrator gate advance.
- source_of_truth: `${run_dir}/artifacts/support_whiteboard.json`.
- fallback: `local_librarian` 不可用或检索异常时仅记录 agent whiteboard note，不阻断 dispatch 执行。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 在 prompt 文本宣称已协同但不写 whiteboard artifact。
  - 仅客服侧白板，生产链路不消费。
  - provider 执行不读取 whiteboard snapshot。
- user_visible_effect:
  - 客服与生产 agent 共享同一 librarian/whiteboard 语境，减少重复追问与上下文断裂。
  - 生产 prompt 可直接看到 support 与 librarian 的最新协作记录。

### DoD Mapping (from request)

- [x] DoD-1: dispatch 写入生产 agent request/result 到共享 whiteboard，并挂接 librarian 线索。
- [x] DoD-2: manual_outbox 与 api_agent prompt 注入 whiteboard snapshot/librarian hits。
- [x] DoD-3: 共享白板与客服通道复用同一路径，不再 support/production 分裂。
- [x] DoD-4: targeted regression + triplet guard 通过。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 在 `ctcp_dispatch` 增加 whiteboard state helper，dispatch 前后写入 agent/librarian 交互条目，并把 snapshot 注入 request。
2) 更新 `manual_outbox` prompt 渲染，追加 whiteboard 上下文段。
3) 更新 `api_agent` prompt 渲染，追加 whiteboard 上下文段。
4) 补充 provider/dispatch 相关回归测试。
5) 执行 targeted tests + triplet guard + canonical verify，并回填结果到 CURRENT/LAST。

### Notes / Decisions

- Default choices made: 复用 `artifacts/support_whiteboard.json` 作为共享白板真源，不新建并行白板文件。
- Alternatives considered: 新建 `artifacts/agent_whiteboard.json`；拒绝（会造成客服与生产上下文分叉）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 若出现 whiteboard 注入缺失/用户可见泄漏回归，将在本轮结果中补 issue memory 记录；当前先按无新增故障处理。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository-local runtime wiring refinement and not yet a stable reusable multi-repo skill asset.

### Results (2026-03-10 - support+production shared whiteboard/librarian wiring)

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/manual_outbox.py`
  - `tools/providers/api_agent.py`
  - `tests/test_provider_selection.py`
  - `tests/test_api_agent_templates.py`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m py_compile scripts/ctcp_dispatch.py tools/providers/manual_outbox.py tools/providers/api_agent.py tests/test_provider_selection.py tests/test_api_agent_templates.py` => `0`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-182611` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-183059` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（ultimate recheck after final report sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-183547` (`passed=14 failed=0`)

- Queue status update suggestion (`todo/doing/done/blocked`): `done` (shared whiteboard+librarian wiring for support+production completed and verified).

## Update 2026-03-10 - 客服用户可见通知去机械化统一闸门

### Queue Binding
- Queue Item: `ADHOC-20260310-support-customer-visible-de-mechanicalization`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 让用户看到的客服回复始终保持自然客服口径，不再暴露内部 agent、artifact 文件名、raw 异常或模板化 PM 兜底话术。
- Scope:
  - 收敛 Telegram 客服里 report / bundle / dispatch / result / write-fail 等用户可见通知到同一自然客服出口。
  - 保持无 active run 的寒暄/致谢/能力询问为本地客服回复，不为这类消息创建 run。
  - 收敛 `ctcp_support_bot.py` 的 provider/model fallback，避免退回机械模板。
  - 补充针对泄漏分支、fallback 以及数据集期望的回归测试。
- Out of scope:
  - dispatch/orchestrator 主执行语义变更。
  - frontend bridge 新能力扩展。
  - 新 provider/模型接入。

### Task Truth Source (single source for current task)

- task_purpose: 把客服所有用户可见通知统一收敛到自然客服 reply gate，消除内部术语泄漏和机械模板兜底，并确保纯寒暄不会误触发 run 创建。
- allowed_behavior_change:
  - `tools/telegram_cs_bot.py` 可以新增/复用统一 customer notice helper，替换 direct `tg.send(...)` 的系统化通知分支。
  - `scripts/ctcp_support_bot.py` 可以调整 fallback / smalltalk / normalize reply 文案与本地 provider 选择策略，但不得改变其 run_dir 证据链结构。
  - `tests/test_telegram_cs_bot_employee_style.py`、`tests/test_support_bot_humanization.py`、`tests/fixtures/telegram_bot_dataset_v1/cases.jsonl` 可以更新为新的自然客服期望。
  - `ai_context/problem_registry.md`、`meta/reports/LAST.md`、`meta/tasks/CURRENT.md` 可记录本轮问题记忆和验证证据。
- forbidden_goal_shift:
  - 不得新增绕过 CTCP bridge/runtime contract 的并行执行路径。
  - 不得仅靠 prompt 改字面而保留 direct raw internal notice 出口。
  - 不得把内部文件名、日志路径、异常堆栈直接回显给用户。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/fixtures/telegram_bot_dataset_v1/cases.jsonl`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `frontend/*`
  - `src/` / `include/`
- completion_evidence:
  - report / bundle / dispatch / result / write-fail 等用户可见通知不再泄漏 `verify_report.json`、`failure_bundle.zip`、`internal agent`、raw exception。
  - 无 active run 的寒暄/能力询问保持本地客服回复，不创建 run。
  - targeted tests + triplet guard 通过，canonical verify 执行并记录结果。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - Telegram 客服入口是 `tools/telegram_cs_bot.py::Bot._handle_message`，support bot 入口是 `scripts/ctcp_support_bot.py::process_message`。
- Downstream consumer analysis:
  - 用户可见回复统一经 `_send_customer_reply` / `support_reply.json.reply_text` 输出；执行桥接状态仍由 run_dir artifacts / events / logs 驱动。
- Source of truth:
  - 用户可见文本真源是 Telegram customer reply payload 与 `artifacts/support_reply.json`。
  - 当前会话真源是 `artifacts/support_session_state.json` 与 session binding DB。
- Current break point / missing wiring:
  - 一批 direct `tg.send(...)` 分支绕过统一闸门，直接暴露内部话术；support bot fallback 仍会退回固定模板。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: Telegram text turn / support-bot stdin|telegram entry.
- current_module: customer notice helper paths in `tools/telegram_cs_bot.py` + fallback normalization in `scripts/ctcp_support_bot.py`.
- downstream: `_send_customer_reply` / `support_reply.json.reply_text` -> user-visible customer wording; run_dir state/logs remain internal.
- source_of_truth: customer reply payloads, `artifacts/support_reply.json`, `artifacts/support_session_state.json`, bound run mapping.
- fallback: provider/router/model 失败时降级为自然客服回复，不暴露 raw internal labels；无 run 的小聊 stays local。
- acceptance_test:
  - `python -m py_compile tools/telegram_cs_bot.py scripts/ctcp_support_bot.py tests/test_telegram_cs_bot_employee_style.py tests/test_support_bot_humanization.py`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_dataset_v1.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 新增 direct `tg.send(...)` 用户通知绕过 `_send_customer_reply`。
  - report/bundle/fallback 分支直接输出 artifact 文件名或内部 agent 标签。
  - 用 prompt 文字掩盖，但保留 run 创建/状态变更误触发路径。
- user_visible_effect:
  - 用户只会看到自然客服口径，即使在失败、报告缺失、agent 回退、写入失败等异常路径也不会被内部系统话术打断。
  - 纯寒暄/致谢/能力询问会得到本地自然回复，不再被误当成新项目立项。

### DoD Mapping (from request)

- [x] DoD-1: Telegram 客服的 report / bundle / dispatch / result / write-fail 通知统一走自然客服出口。
- [x] DoD-2: 无 active run 的 smalltalk/capability/thanks 保持本地回复，不创建 run。
- [x] DoD-3: support bot fallback 不再回退到机械模板。
- [x] DoD-4: targeted regression + dataset + triplet guard + canonical verify 记录到案。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 收敛 Telegram 客服 direct notice 分支，改走统一 customer reply gate。
2) 收敛 support bot fallback / smalltalk / normalize reply 文案，保证 provider 失败时仍是客户口径。
3) 更新数据集与人性化回归测试，覆盖 report/bundle/dispatch/result/fallback 与 unbound smalltalk。
4) 执行 targeted tests + triplet guard + canonical verify，并把首个失败点/最终结果回填到 CURRENT/LAST。

### Notes / Decisions

- Default choices made: 优先改 executable code routing，不接受仅改 prompt 文本的“表面人性化”。
- Alternatives considered: 仅更新模板文案；拒绝，因为 direct `tg.send(...)` 泄漏路径仍会存在。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 记录“用户可见内部系统话术泄漏”到 `ai_context/problem_registry.md`，作为后续客服分支审查模板。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a repo-specific runtime hardening pass rather than a reusable standalone skill.

### Results (2026-03-10 - 客服用户可见通知去机械化统一闸门)

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `ai_context/problem_registry.md`
  - `tools/telegram_cs_bot.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/fixtures/telegram_bot_dataset_v1/cases.jsonl`

- Verification summary:
  - `python -m py_compile tools/telegram_cs_bot.py scripts/ctcp_support_bot.py tests/test_telegram_cs_bot_employee_style.py tests/test_support_bot_humanization.py` => `0`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (32 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (21 passed)
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_dataset_v1.py" -v` => `0` (1 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (18 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure gate: `python unit tests`
    - first failure detail: `tests/test_support_bot_suite_v1.py` cases `C02/T03/T08` flagged bare `继续` reply text as exact user-text echo because continuation wording still used the same token.
    - minimal fix strategy: change local continuation Chinese phrasing to `接着往下` style and add a direct regression for `build_employee_note_reply("继续", "zh")`.
  - `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py` => `0`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (33 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_suite_v1.py" -v` => `0` (2 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-001313` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST/queue sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-001825` (`passed=14 failed=0`)

- Queue status update suggestion (`todo/doing/done/blocked`): `done`

## Update 2026-03-11 - 设计目标改为机械层定边界、agent 定表述

### Queue Binding

- Queue item: `ADHOC-20260311-boundary-first-support-expression`
- Scope lane: support reply design contract / support-bot fallback
- Why now:
  - 用户要求把当前客服设计目标从“固定结构输出”明确改成“让机械层只决定边界，让 agent 决定表述”。
  - 现有文档与 support-bot 默认 prompt 仍残留“三段式强制表达”的旧口径，需要同步到新的设计真源。

### Scope / Non-goals

- In scope:
  - 把 `docs/10_team_mode.md` 的客服目标改为边界驱动而非固定三段式。
  - 把 `agents/prompts/support_lead_reply.md` 与 `scripts/ctcp_support_bot.py` 默认 prompt/fallback 契约改成“机械层定边界、agent 自然表述”。
  - 补支持这条设计目标的最小回归。
- Out of scope:
  - 重写 Telegram 全部 status / advance 口径生成器。
  - 改动 runtime bridge、dispatcher、provider 选择逻辑。
  - 重写历史报告中的旧任务描述。

### Task Truth Source (single source for current task)

- task_purpose: 把客服设计目标从固定句式约束切换为边界约束，让机械层只负责泄漏防护、问题数量和动作推进，具体表述交给 agent 自然生成。
- allowed_behavior_change:
  - `docs/10_team_mode.md` 可更新 Telegram / support-bot 的设计目标与双通道说明。
  - `agents/prompts/support_lead_reply.md` 与 `scripts/ctcp_support_bot.py` 可收紧为边界契约而非固定模板契约。
  - `tests/test_support_bot_humanization.py` 可新增与默认 prompt / fallback 相关的回归。
  - `meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录本轮任务 truth 与证据。
- forbidden_goal_shift:
  - 不得把本轮扩展成 Telegram 全量客服回复重写。
  - 不得引入新的固定格式替代“三段式”。
  - 不得放松内部信息泄漏、最多一个关键问题、每轮推进一个动作这些边界。
- in_scope_modules:
  - `docs/10_team_mode.md`
  - `agents/prompts/support_lead_reply.md`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `frontend/*`
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/*`
- completion_evidence:
  - `docs/10_team_mode.md` 明确写出“让机械层只决定边界，让 agent 决定表述”。
  - support-lead prompt/default prompt 都把边界与表述职责拆开。
  - fallback normalize 不再拼固定三段壳，相关回归与 canonical verify 通过。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 客服回复设计真源主要落在 `docs/10_team_mode.md`、`agents/prompts/support_lead_reply.md`、`scripts/ctcp_support_bot.py`。
- Downstream consumer analysis:
  - `scripts/ctcp_support_bot.py::build_support_prompt` 读取 prompt 模板，provider 与 fallback 文案都受这层契约影响。
- Source of truth:
  - 设计真源：`docs/10_team_mode.md`
  - 生成约束真源：`agents/prompts/support_lead_reply.md` 与 `scripts/ctcp_support_bot.py::default_prompt_template`
- Current break point / missing wiring:
  - 文档和默认 prompt 已经自然化了一部分，但仍保留“固定三段式”的设计口径，导致目标与运行契约不完全一致。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: 客服设计原则 -> `docs/10_team_mode.md` -> support prompt builder / fallback reply normalization。
- current_module: `agents/prompts/support_lead_reply.md` + `scripts/ctcp_support_bot.py`
- downstream: `build_support_prompt` 提供给 provider 的 prompt，以及 provider/fallback 无法直接使用时的 `normalize_reply_text` 输出。
- source_of_truth: `docs/10_team_mode.md`, `agents/prompts/support_lead_reply.md`, `scripts/ctcp_support_bot.py`
- fallback: provider/fallback 仍必须 customer-facing，但不再用固定三段壳拼装；边界仍由机械层兜底。
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 只改 `docs/10_team_mode.md` 口号，不改 prompt/default fallback 契约。
  - 用新的固定结构替换旧的三段式。
  - 放宽 customer-facing 内部泄漏过滤来换取“更自然”。
- user_visible_effect:
  - 设计目标从“机械层决定句式”切到“机械层只定边界”；support-bot 的兜底回复更自然，不再隐含固定三段骨架。

### DoD Mapping (from request)

- [x] DoD-1: 文档设计目标明确改为“让机械层只决定边界，让 agent 决定表述”。
- [x] DoD-2: support lead prompt/default prompt 改成边界驱动、不强制固定模板。
- [x] DoD-3: support-bot fallback normalize 改为自然兜底而非固定三段拼接。
- [x] DoD-4: targeted tests + canonical verify 回填到案。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code/doc changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 更新 team-mode 设计目标与双通道说明。
2) 更新 support lead prompt 与 support-bot 默认 prompt/fallback 契约。
3) 补最小回归，验证 boundary-first 设计已落到运行层。
4) 执行 targeted tests + canonical verify，并把结果回填到 CURRENT/LAST。

### Notes / Decisions

- Default choices made: 这轮只改设计真源、prompt 默认值和 fallback normalization，不扩展到 Telegram 全量状态文案重写。
- Alternatives considered: 直接全量替换 `tools/telegram_cs_bot.py` 里的 `_compose_three_part_reply`；拒绝，因为会超出本轮“设计目标切换”的范围。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: None.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: yes (`ctcp-workflow` -> `ctcp-verify`)。

### Results (2026-03-11 - 设计目标改为机械层定边界、agent 定表述)

- Files changed:
  - `docs/10_team_mode.md`
  - `agents/prompts/support_lead_reply.md`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (22 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (18 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-093225` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-093730` (`passed=14 failed=0`)

- Queue status update suggestion (`todo/doing/done/blocked`): `done`

## Update 2026-03-11 - Telegram 新建 run 的执行 provider 对齐

### Queue Binding
- Queue Item: `ADHOC-20260311-telegram-run-provider-alignment`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 修正 Telegram bot 的项目入口流程，避免无 run 的寒暄走本地回复、但真正建项目时又因为错误的 `api_agent` 默认而立刻 401。
- Scope:
  - 在 Telegram 新建 run 后校准该 run 的工程 dispatch provider。
  - 识别 `OPENAI_API_KEY=ollama` 且无 `OPENAI_BASE_URL` 的误配置，不再把它当成外部 API 可用。
  - 补充 run 创建/provider readiness 回归。
- Out of scope:
  - 全局 workflow recipe 默认 provider 重设计。
  - 扩展 CTCP dispatcher 的角色 provider 支持矩阵。
  - 新模型/provider 接入。

### Task Truth Source (single source for current task)

- task_purpose: 让 Telegram-created run 的工程执行链与真实可用的运行时对齐，消除“寒暄可答但项目一启动就 API 401”的错位流程。
- allowed_behavior_change:
  - `tools/telegram_cs_bot.py` 可在 `_create_run` 后补 run 级别的 dispatch_config 对齐逻辑。
  - `tools/providers/api_agent.py` 可收紧 API readiness 判定，拦截 ollama placeholder key 无 base_url 的误配置。
  - `tests/test_api_agent_templates.py` 与 `tests/test_telegram_cs_bot_employee_style.py` 可新增相关回归。
  - `docs/10_team_mode.md`、`ai_context/problem_registry.md`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录新的运行约束与证据。
- forbidden_goal_shift:
  - 不得把这轮修改扩展成全局 dispatch 架构重写。
  - 不得破坏纯寒暄本地回复路径。
  - 不得继续让 Telegram-created run 在明显误配置的 API 环境下默认走 `api_agent`。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `tools/providers/api_agent.py`
  - `docs/10_team_mode.md`
  - `ai_context/problem_registry.md`
  - `tests/test_api_agent_templates.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/*`
- completion_evidence:
  - Telegram-created run 在 `OPENAI_API_KEY=ollama` 且无 `OPENAI_BASE_URL` 时不再保留 `api_agent` 为执行默认。
  - `api_agent` readiness 明确拒绝上述误配置。
  - targeted tests + canonical verify 通过并记录结果。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户寒暄入口走 `Bot._handle_message` 的 local smalltalk 分支；项目立项入口走 `Bot._create_run` -> `ctcp_orchestrate new-run`。
- Downstream consumer analysis:
  - run 创建后真正执行链读取 `artifacts/dispatch_config.json` 并由 `ctcp_dispatch` 解析 provider。
- Source of truth:
  - run 级 provider 真源是 `${run_dir}/artifacts/dispatch_config.json`。
  - API readiness 真源是 `OPENAI_API_KEY` / `CTCP_OPENAI_API_KEY` + `OPENAI_BASE_URL` / `CTCP_OPENAI_BASE_URL`。
- Current break point / missing wiring:
  - smalltalk 本地回复与工程执行 provider 选择没有对齐；`api_agent` 对 placeholder key 的 readiness 判断过宽。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: Telegram message -> `_handle_message` -> `_create_run`.
- current_module: run-level dispatch alignment in `tools/telegram_cs_bot.py` + provider readiness guard in `tools/providers/api_agent.py`.
- downstream: run_dir `dispatch_config.json` -> `ctcp_dispatch.load_dispatch_config` / `api_agent._resolve_templates`.
- source_of_truth: `${run_dir}/artifacts/dispatch_config.json`, process env for OpenAI/API settings.
- fallback: external API env not ready -> Telegram-created run downgrades to `manual_outbox` instead of broken `api_agent`; greeting/smalltalk stays local as before.
- acceptance_test:
  - `python -m py_compile tools/providers/api_agent.py tools/telegram_cs_bot.py tests/test_api_agent_templates.py tests/test_telegram_cs_bot_employee_style.py`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 仅靠用户提示解释 API 不可用，但不修 provider 选择。
  - 继续把 `OPENAI_API_KEY=ollama` 无 base_url 当成可用外部 API。
  - 为 greeting/smalltalk 人为创造 run 来掩盖 provider 错位。
- user_visible_effect:
  - 用户仍可在第一句寒暄得到本地回复。
  - 真正建项目时不会再因为错误 API 默认而立刻遇到 401 阻塞。

### DoD Mapping (from request)

- [x] DoD-1: 查清为什么第一句能回答但下一句显示不能调用。
- [x] DoD-2: Telegram-created run 在外部 API 误配置时不再默认走 broken `api_agent`。
- [x] DoD-3: `api_agent` 明确拦截 ollama placeholder key 无 base_url 的误配置。
- [ ] DoD-4: targeted tests + canonical verify 回填到案。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 在 `api_agent` 增加误配置守卫，识别 `OPENAI_API_KEY=ollama` 且缺 base_url 的情况。
2) 在 Telegram `_create_run` 后对 run 级 dispatch_config 做 provider 对齐。
3) 补 run 创建/provider readiness 回归。
4) 执行 targeted tests + canonical verify，并把首个失败点/最终结果回填到 CURRENT/LAST。

### Notes / Decisions

- Default choices made: 不改全局 recipe 默认，只修 Telegram-created run 的 provider 对齐。
- Alternatives considered: 直接扩展 dispatcher 让所有角色都支持 `ollama_agent`；拒绝，因为会越过当前 docs/contract 的 provider 矩阵边界。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 记录“ollama placeholder key 被误判为外部 API ready”到 `ai_context/problem_registry.md`。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a repository-local runtime correction tied to current Telegram execution wiring.

### Results (2026-03-11 - Telegram 新建 run 的执行 provider 对齐)

- Files changed:
  - `tools/telegram_cs_bot.py`
  - `tools/providers/api_agent.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `docs/10_team_mode.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m py_compile tools/providers/api_agent.py tools/telegram_cs_bot.py tests/test_api_agent_templates.py tests/test_telegram_cs_bot_employee_style.py` => `0`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (9 passed)
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (34 passed)
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (21 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (18 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-005125` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST/queue sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-005619` (`passed=14 failed=0`)

- Queue status update suggestion (`todo/doing/done/blocked`): `done`
