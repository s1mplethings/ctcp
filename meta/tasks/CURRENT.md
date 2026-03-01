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

## Update 2026-03-01 - 客户可理解的项目进度口径

### Context
- 用户要求项目播报直接可被客户理解，重点是“现在打算做什么功能、做完什么功能、关键问题是什么”。  

### DoD Mapping (from request)
- [x] DoD-1: `status` 输出包含“现在打算做 / 刚做完 / 关键问题”三段式。
- [x] DoD-2: `advance` 输出改为客户口径，避免仅给内部流水状态。
- [x] DoD-3: TRACE 主动推送优先总结“Done / Doing / Key issue”。
- [x] DoD-4: 增加测试覆盖新口径函数。
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
