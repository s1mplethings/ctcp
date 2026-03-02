# Task - pointcloud-project-generator-and-dialogue-bench

## Queue Binding
- Queue Item: `N/A (user-requested task pack)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- User requested a full CTCP task pack upgrade for point-cloud workflows:
  - `scaffold-pointcloud`: generate complete source project from templates into target `--out`
  - `cos-user-v2p`: run dialogue-driven external benchmark and copy outputs to fixed destination
- Scope:
  - add new CLI subcommand + template rendering + `meta/manifest.json`
  - enforce safety and doc-first run evidence (`SCAFFOLD_PLAN.md` / `USER_SIM_PLAN.md`)
  - ensure testkit execution is outside both CTCP repo and tested repo
  - add fixtures, SimLab scenario, behavior docs, and unit tests

## DoD Mapping (from request)
- [x] DoD-1: `scaffold-pointcloud` command generates required minimal/standard point-cloud project files.
- [x] DoD-2: `cos-user-v2p` runs benchmark with dialogue evidence and fixed output copy path.
- [x] DoD-3: both commands create run_dir doc-first evidence and auditable trace/report.
- [x] DoD-4: fixtures/tests/simlab/behavior docs are added and wired.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: update task/report + behavior docs and index registration.
2) Implement `scaffold-pointcloud` in `scripts/ctcp_orchestrate.py`.
3) Strengthen `cos-user-v2p` + `tools/testkit_runner.py` location/verify defaults.
4) Add templates/fixtures/tests/simlab scenario.
5) Run targeted tests + full `scripts/verify_repo.ps1`.
6) Record final evidence in `meta/reports/LAST.md`.

## Notes / Decisions
- Reuse existing dialogue machinery in orchestrator for deterministic script/agent/default answer modes.
- Keep legacy `scaffold` command unchanged; add independent `scaffold-pointcloud` command.

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
