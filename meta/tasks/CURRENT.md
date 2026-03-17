# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260317-support-previous-project-status-grounding.md`](archive/20260317-support-previous-project-status-grounding.md)
- Date: 2026-03-17
- Topic: Support 旧项目进度追问绑定真实 run 状态
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260317-support-previous-project-status-grounding`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 17:41 live Telegram transcript 表明用户追问“我之前那个项目做成什么样子了”时，support lane 没有给出真实 run 进展，而是把该句当成新的项目细化并回成“请提供最新规划文档”。
- Dependency check: `ADHOC-20260317-support-proactive-baseline-preserve-on-greeting` = `done`.
- Scope boundary: 只修 active support session 上“旧项目/之前项目”的状态追问识别、brief 保留与 grounded status reply；不改 bridge API，不回退主动推送，不改 provider 栈。

## Task Truth Source (single source for current task)

- task_purpose: 让 active support session 上“之前那个项目/之前的项目做成什么样子了”这类 status-like follow-up 绑定到已存在的 bound run 进展，而不是被误当成新的 `PROJECT_DETAIL` 需求并触发新的 planning/file-request 动作。
- allowed_behavior_change: 可更新 `frontend/conversation_mode_router.py`、`scripts/ctcp_support_bot.py`、`docs/10_team_mode.md`、`tests/test_frontend_rendering_boundary.py`、`tests/test_support_bot_humanization.py`、`ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260317-support-previous-project-status-grounding.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260317-support-previous-project-status-grounding.md`。
- forbidden_goal_shift: 不得靠关闭项目 follow-up 路由来规避；不得改 `scripts/ctcp_front_bridge.py` 对外语义；不得把“旧项目状态追问”变成纯模板壳而绕开真实 run 进展。
- in_scope_modules:
  - `frontend/conversation_mode_router.py`
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `tests/test_frontend_rendering_boundary.py`
  - `tests/test_support_bot_humanization.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260317-support-previous-project-status-grounding.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260317-support-previous-project-status-grounding.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `tests/test_runtime_wiring_contract.py`
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/`
- completion_evidence: old-project status follow-ups now命中 `STATUS_QUERY` / grounded progress path，不再覆盖 project brief；focused regressions 通过；Telegram bot 以新代码重启；canonical verify 已执行并记录最终结果。

## Analysis / Find (before plan)

- Entrypoint analysis: `process_message()` 当前通过 `detect_conversation_mode()` 判断 turn 类型；live 证据显示“我想要知道我之前那个项目做成什么样子了”没有命中 `STATUS_QUERY`，而是走成 `PROJECT_DETAIL`，随后 `sync_project_context()` 把该句写回 session brief 并通过 bridge 触发新的 whiteboard/file-request 轨迹。
- Live runtime evidence: `support_reply.json` 对这句追问返回“是否方便提供最新规划文档”；`support_session_state.json` 中 `task_summary/project_brief` 被该句覆盖；`support_whiteboard.json` 追加了 `chair/file_request` 和 `librarian/context_pack`，而 bound run 真实 goal 仍是“我想要你继续优化我的vn项目”。
- Root-cause detail: status-like phrase库没有覆盖“之前那个项目做成什么样子了”这类旧项目进度追问，且 `should_refresh_project_brief()` 只看项目 goal marker，导致该句在误分类后会直接覆盖已有 brief。
- Source of truth: `frontend/conversation_mode_router.py`、`scripts/ctcp_support_bot.py`、`docs/10_team_mode.md`、live session `6092527664` 的 `support_session_state.json` / `support_reply.json` / `events.jsonl`、bound run `20260316-220645-742889-orchestrate` 的 `RUN.json` / `artifacts/support_whiteboard.json`、focused tests、`scripts/verify_repo.ps1`。
- Current break point / missing wiring: “旧项目状态追问”缺少稳定的 `STATUS_QUERY` 识别和 brief-preserve guard，导致状态查询误入 project-detail 规划路径。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: 用户给出 17:39/17:41 live Telegram transcript，显示“之前那个项目做成什么样子了”被误答成需要最新规划文档。
- current_module: `frontend.conversation_mode_router` + `ctcp_support_bot` 的 conversation-mode / project-brief / bridge-sync 组合逻辑。
- downstream: active bound run 的 status reply 路径、support session brief 稳定性，以及 whiteboard 是否误追加新的 planning/file-request。
- source_of_truth: live support session `6092527664` artifacts、bound run `20260316-220645-742889-orchestrate` artifacts、当前脚本与 focused regressions。
- fallback: 若 canonical verify 失败，只记录新的首个失败点并停在该点。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得把 active-run follow-up 全部粗暴改成 `STATUS_QUERY` 以破坏真正的项目细化输入
  - 不得让状态回复绕开真实 run truth 只靠模板硬写
  - 不得泄漏内部 trace/logs
- user_visible_effect: 用户追问“之前那个项目现在做成什么样了”时，应直接收到基于 bound run 的具体进展，而不是被要求重新补规划文档。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: status-like follow-ups about the previous or earlier project on an active support session route through the status/progress path instead of project-detail replanning
- [x] DoD-2: those follow-ups do not overwrite the current project brief or trigger fresh planning/file-request work on the already bound run
- [x] DoD-3: focused regressions plus canonical verify and a Telegram bot restart are executed and recorded

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local runtime/code scan only)
- [x] Code changes allowed (`Scoped previous-project status grounding + runtime restart only`)
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind a narrow previous-project status-grounding task.
2) Teach the support lane to classify old-project progress follow-ups as `STATUS_QUERY` on active sessions and keep them from replacing the current project brief.
3) Add focused regressions for routing, brief preservation, and grounded status reply behavior.
4) Re-run focused tests and canonical verify.
5) Restart the Telegram bot on the new code and confirm the live runtime no longer asks for fresh planning docs on old-project status follow-ups.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - live inbox evidence: `2026-03-17T09:41:01Z` 用户发送 `我想要知道我之前那个项目做成什么样子了`
  - live reply evidence: `support_reply.json.reply_text` 回成“是否方便提供最新规划文档”
  - live session evidence: `support_session_state.json.task_summary/project_memory.project_brief` 被这句覆盖
  - live whiteboard evidence: 同一 turn 追加 `chair/file_request` 与 `librarian/context_pack`
  - contrast: 该句应消费已绑定 run 的现有 status/whiteboard 进展，而不是开启新的 planning/file-request 轮次

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `conversation_mode_router/detect_conversation_mode -> sync_project_context -> build_final_reply_doc`
  - accumulated: active session 的 `task_summary/project_brief` 继续保留真实项目 brief，不被旧项目状态追问覆盖
  - consumed: repair 必须被 focused regressions、重启后的 live bot 和 canonical verify 消费

## Notes / Decisions

- Default choices made: 保留现有 grounded progress reply 路径，优先修状态追问识别与 brief-preserve guard，不新增第二套旧项目状态模板。
- Alternatives considered: 仅在 provider prompt 层教模型别问规划文档；不采纳，因为 live 误行为已经进入 bridge/whiteboard 和 session state，必须从 runtime 路由与记忆更新层修。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: required; 这是 live Telegram 可见路径下的状态追问误路由，修复状态会记录到 `ai_context/problem_registry.md`。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: yes; this task uses `ctcp-workflow` for bounded execution and `ctcp-verify` for final canonical gate.
- persona_lab_impact: none; 这是 runtime dedupe/notification 语义，不改 style rubric。

## Results

- Files changed:
  - `frontend/conversation_mode_router.py`
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `tests/test_frontend_rendering_boundary.py`
  - `tests/test_support_bot_humanization.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260317-support-previous-project-status-grounding.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260317-support-previous-project-status-grounding.md`
- Verification summary: focused py_compile + `test_frontend_rendering_boundary.py` + `test_support_bot_humanization.py` passed; canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` passed with lite replay summary `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260317-180318\summary.json`; Telegram bot restarted as PID `37072`.
- Queue status update suggestion (`todo/doing/done/blocked`): done.

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-17 | Support 旧项目进度追问绑定真实 run 状态 | [→](archive/20260317-support-previous-project-status-grounding.md) |
| 2026-03-17 | Support greeting turn 保留主动进度基线 | [→](archive/20260317-support-proactive-baseline-preserve-on-greeting.md) |
| 2026-03-17 | Support 主动推送误复用寒暄修复 | [→](archive/20260317-support-proactive-push-greeting-dup-guard.md) |
| 2026-03-16 | Support 主动进度推送与旧大纲恢复 | [→](archive/20260316-support-proactive-progress-and-resume.md) |
| 2026-03-16 | Support 状态/进度回复绑定真实 run 进展 | [→](archive/20260316-support-status-progress-grounding.md) |
| 2026-03-16 | Support greeting 泄露旧项目/旧交付上下文硬化 | [→](archive/20260316-support-greeting-stale-context-hardening.md) |
| 2026-03-16 | Support 对话场景先分流再回复 | [→](archive/20260316-support-conversation-situation-routing.md) |
| 2026-03-16 | SimLab fixer-loop 回归修复（S15 / S16） | [→](archive/20260316-simlab-fixer-loop-repair.md) |
| 2026-03-16 | Telegram 测试到项目生成 smoke 联通与启动检查 | [→](archive/20260316-telegram-to-project-generation-smoke.md) |
| 2026-03-16 | Markdown 流程拆清与逐条表达 | [→](archive/20260316-markdown-flow-clarity.md) |
| 2026-03-16 | 全项目健康检查与阻塞问题审计 | [→](archive/20260316-repo-health-audit.md) |

Full archive: `meta/tasks/archive/`
