# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260321-src-functional-boundary-refactor.md`](archive/20260321-src-functional-boundary-refactor.md)
- Date: 2026-03-21
- Topic: src 功能边界拆分（Bridge 瘦身 + 单一文件操作适配层）
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260321-src-functional-boundary-refactor`
- Layer/Priority: `L2 / P1`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户明确要求开始修改 `src` 功能区分，目标是降低 Bridge 过载和桥接层职责重叠。
- Dependency check: `ADHOC-20260317-support-frontdesk-state-machine` = `done`.
- Scope boundary: 仅做 Bridge/SddaiBridge 职责拆分与图视图投影模块化；不改 support lane / orchestrator / provider 链路。

## Task Truth Source (single source for current task)

- task_purpose: 让 GUI `src` 层的职责边界更清晰，减少 `Bridge` 同时承担 orchestration + view projection + file I/O 的混合职责。
- allowed_behavior_change: 可更新 `include/Bridge.h`、`src/Bridge.cpp`、`include/GraphViewProjector.h`、`src/GraphViewProjector.cpp`、`src/MainWindow.cpp`、`CMakeLists.txt`、`artifacts/PLAN.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260321-src-functional-boundary-refactor.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260321-src-functional-boundary-refactor.md`。
- forbidden_goal_shift: 不得引入无关重构；不得改变 support/frontend 用户可见回复语义；不得跳过 canonical verify；不得扩展到 backend orchestrator 主题。
- in_scope_modules:
  - `include/Bridge.h`
  - `src/Bridge.cpp`
  - `include/GraphViewProjector.h`
  - `src/GraphViewProjector.cpp`
  - `src/MainWindow.cpp`
  - `CMakeLists.txt`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260321-src-functional-boundary-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260321-src-functional-boundary-refactor.md`
- out_of_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `frontend/`
  - `tools/providers/`
  - `scripts/ctcp_orchestrate.py`
  - `persona_lab/`
- completion_evidence: Bridge 的视图投影被独立模块承接，Bridge 与 SddaiBridge 的文件操作边界去重，canonical verify 命令和结果写入 LAST 报告并通过。

## Analysis / Find (before plan)

- Entrypoint analysis: `src/main.cpp -> MainWindow -> SddaiBridge/Bridge` 是 GUI 入口；原 `Bridge::requestGraph(view, focus)` 同时承担视图构造与输出裁剪。
- Downstream consumer analysis: web 端通过 `QWebChannel` 消费 `SddaiBridge`；`MainWindow` 文件树双击原先直接调用 `Bridge::openFile`。
- Source of truth: `AGENTS.md`、`meta/tasks/CURRENT.md`、`include/Bridge.h`、`src/Bridge.cpp`、`src/sddai_bridge.h`、`src/sddai_bridge.cpp`、`CMakeLists.txt`。
- Current break point / missing wiring: `Bridge` 与 `SddaiBridge` 都暴露文件打开/读取能力，且 `Bridge.cpp` 包含 Summary/Pipeline 视图投影细节，职责过载。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `MainWindow` 双击动作 + web channel 调用 `bridge.requestGraph/openPath/openNode`。
- current_module: `Bridge`（图构建编排）与 `SddaiBridge`（WebChannel 适配 + 安全路径文件访问）。
- downstream: `web/graph_spider/spider.js` 通过 WebChannel 获取图和打开路径。
- source_of_truth: Graph 数据源仍由 `ProjectScanner/SpecExtractor/SchemaLoader/MetaStore/RunLoader/GraphBuilder/LayoutEngine` 组合输出。
- fallback: 若 verify 失败，只记录首个失败 gate，并给出最小修复路径后重跑。
- acceptance_test:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得只改注释或文档而不完成实际边界拆分
  - 不得在同一 patch 混入 support lane 逻辑修补
  - 不得跳过 `meta/reports/LAST.md` 命令证据记录
- user_visible_effect: 用户侧功能保持一致（图加载/打开文件行为不变），但代码边界更清晰，后续维护变更风险更低。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Bridge graph-view projection logic is extracted into a dedicated projector module so core bridge no longer owns Summary/Pipeline projection details
- [x] DoD-2: Bridge and SddaiBridge no longer overlap on file-open/read APIs; file opening and safe file reading stay in SddaiBridge while Bridge focuses on project graph orchestration
- [x] DoD-3: build wiring and canonical verify are executed, with command evidence, first failure point, and minimal fix strategy recorded

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local runtime/code scan only)
- [x] Code changes allowed (`Scoped Bridge/SddaiBridge boundary refactor + graph-view projection extraction`)
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind queue item and current task card before code edits.
2) Extract `Bridge::requestGraph(view, focus)` projection logic into `GraphViewProjector`.
3) Remove duplicated file APIs from `Bridge` and keep file open/read in `SddaiBridge` only.
4) Update `MainWindow` callsite and `CMakeLists.txt` source list.
5) Run canonical verify.
6) If verify fails, capture first failure and apply minimal fix.
7) Update task/report archives and final closure records.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check: first `verify_repo` failure was `patch_check` scope violation on `CMakeLists.txt`.
  - contrast: task目标不变，失败点只是 PLAN scope 与本次代码变更清单不一致。
  - fix loop: minimal repair was updating `artifacts/PLAN.md` `Scope-Allow` to include `CMakeLists.txt`, `src/`, `include/`; rerun canonical verify then passed.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `MainWindow/SddaiBridge -> Bridge -> GraphBuilder/LayoutEngine` 主链保持连通。
  - accumulated: 视图投影逻辑累计到 `GraphViewProjector`，不再散落在 `Bridge` 里。
  - consumed: `Bridge::requestGraph(view, focus)` 直接消费 projector 输出，web channel 继续消费同结构 JSON。

## Notes / Decisions

- Default choices made: 优先做“不改行为”的结构拆分，不触碰 support/backend 主题。
- Alternatives considered: 直接做大规模 pimpl/依赖倒置；暂不采纳，避免超出本轮最小范围。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: no new issue-memory entry for this patch; this is a planned maintainability refactor without新的用户可见失败复现。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch is a one-off repo-local boundary refactor, not a reusable workflow asset.
- persona_lab_impact: none.

## Results

- Files changed:
  - `include/Bridge.h`
  - `src/Bridge.cpp`
  - `include/GraphViewProjector.h`
  - `src/GraphViewProjector.cpp`
  - `src/MainWindow.cpp`
  - `CMakeLists.txt`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260321-src-functional-boundary-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260321-src-functional-boundary-refactor.md`
- Verification summary: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` first failed at `patch_check` (out-of-scope path), then passed after minimal Scope-Allow fix; final closure rerun also passed with canonical exit code `0` and lite replay run_dir `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260321-113846`.
- Queue status update suggestion (`todo/doing/done/blocked`): done.

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-21 | src 功能边界拆分（Bridge 瘦身 + 单一文件操作适配层） | [→](archive/20260321-src-functional-boundary-refactor.md) |
| 2026-03-17 | Support frontdesk 显式状态机与任务槽位接线 | [→](archive/20260317-support-frontdesk-state-machine.md) |
| 2026-03-17 | Support 旧项目进度追问绑定真实 run 状态 | [→](archive/20260317-support-previous-project-status-grounding.md) |
| 2026-03-17 | Support greeting turn 保留主动进度基线 | [→](archive/20260317-support-proactive-baseline-preserve-on-greeting.md) |
| 2026-03-17 | Support 主动推送误复用寒暄修复 | [→](archive/20260317-support-proactive-push-greeting-dup-guard.md) |
| 2026-03-16 | Support 主动进度推送与旧大纲恢复 | [→](archive/20260316-support-proactive-progress-and-resume.md) |
| 2026-03-16 | Support 状态/进度回复绑定真实 run 进展 | [→](archive/20260316-support-status-progress-grounding.md) |
| 2026-03-16 | Support greeting 泄露旧项目/旧交付上下文硬化 | [→](archive/20260316-support-greeting-stale-context-hardening.md) |
| 2026-03-16 | Support 对话场景先分流再回复 | [→](archive/20260316-support-conversation-situation-routing.md) |
| 2026-03-16 | SimLab fixer-loop 回归修复（S15 / S16） | [→](archive/20260316-simlab-fixer-loop-repair.md) |

Full archive: `meta/tasks/archive/`
