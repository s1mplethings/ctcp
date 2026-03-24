# Current Task

> **用法**：本文件保留当前活跃任务指针，同时内嵌 workflow gate 所需的最新任务摘要。
> 历史任务正文在 `meta/tasks/archive/`。

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260324-support-mode-router-model-assist.md`](archive/20260324-support-mode-router-model-assist.md)
- Date: 2026-03-24
- Topic: 支持对话模式二段判定（规则首判 + 模型仲裁）
- Status: `blocked`

## Queue Binding

- Queue Item: `ADHOC-20260324-support-mode-router-model-assist`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户反馈 support mode 判定过于机械，要求在“进入什么模式”上引入 API/本地模型判断。
- Dependency check: `ADHOC-20260317-support-frontdesk-state-machine` = `done`.
- Scope boundary: 只修 support lane 的 mode 判定路径与相关合同/回归；不改 CTCP bridge 主流程语义，不改无关模块。

## Task Truth Source (single source for current task)

- task_purpose: 降低 support 对话模式判定的机械误判，保留规则首判并在歧义 turn 上增加模型仲裁（api-first + local fallback）。
- allowed_behavior_change: 可更新 `scripts/ctcp_support_bot.py`、`docs/10_team_mode.md`、`tests/test_support_bot_humanization.py`、`tests/test_runtime_wiring_contract.py`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260324-support-mode-router-model-assist.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260324-support-mode-router-model-assist.md`。
- forbidden_goal_shift: 不得新增模式类型；不得把 mode 判定改成全量仅模型；不得绕过 `ctcp_front_bridge`；不得跳过 canonical verify。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `docs/10_team_mode.md`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-mode-router-model-assist.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-mode-router-model-assist.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_front_bridge.py`
  - `frontend/frontdesk_state_machine.py`
  - `src/`
  - `include/`
- completion_evidence: ambiguous turn 会触发 model-assisted mode arbitration 且可回落到本地；现有 mode 语义保持；focused regressions + canonical verify 通过并留痕。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_support_bot.py::process_message()` 当前先 `detect_conversation_mode()`，仅规则路由。
- Downstream consumer analysis: `conversation_mode` 会驱动 prompt context、bridge 绑定、frontdesk reply strategy、delivery action gating。
- Source of truth: `AGENTS.md`、`docs/00_CORE.md` §0.Z、`docs/10_team_mode.md`、`meta/tasks/CURRENT.md`、`scripts/ctcp_support_bot.py`。
- Current break point / missing wiring: 缺少“规则不确定时由模型仲裁 mode”的 runtime 路径，导致解释/质疑类 turn 容易被压到 `PROJECT_DETAIL` 固定壳。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: Telegram/stdin support 消息入口 `process_message()`。
- current_module: `detect_conversation_mode` + support provider 执行链。
- downstream: `build_support_prompt()`、`sync_project_context()`、`build_final_reply_doc()`、public delivery gating。
- source_of_truth: support session state + frontdesk state + provider JSON artifacts。
- fallback: 模型仲裁失败时保留规则首判 mode，不阻断主回复链。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不得把 unsupported mode 写入 session state
  - 不得引入对 manual_outbox 的用户可见依赖
  - 不得改变 bridge 接线边界
- user_visible_effect: 在模糊/解释型追问上，客服更像“理解上下文后再判断模式”的自然响应，不再机械套壳。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: support runtime keeps deterministic conversation-mode routing as first pass and adds an optional model-assisted second-pass arbitration for ambiguous turns
- [x] DoD-2: mode arbitration uses api-first provider with local fallback and never widens mode set beyond existing support contract modes
- [ ] DoD-3: focused regressions plus canonical verify prove ambiguous turns can be reclassified without breaking existing support routing behavior

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local runtime/code scan only)
- [x] Code changes allowed (`Scoped support mode routing refinement`)
- [ ] Patch applies cleanly (blocked by unrelated preexisting worktree file)
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind queue item and current task card before implementation.
2) Add model-assisted mode arbitration path in `scripts/ctcp_support_bot.py` (api-first + local fallback + safe fallback to rule mode).
3) Keep existing mode set and bridge semantics unchanged.
4) Add focused regressions for arbitration hit and arbitration fallback.
5) Update support lane contract note in `docs/10_team_mode.md`.
6) Run focused tests then canonical verify.
7) Record first failure (if any), minimal repair, and close task/report archive evidence.

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` failed at workflow gate (`LAST.md not updated`).
  - contrast-1: code change本身未触发行为校验失败，首个失败点是流程证据文件缺失。
  - fix-1: update `meta/reports/LAST.md` + archive report topic.
  - check-2: rerun canonical verify failed at workflow gate (`LAST.md missing triplet issue-memory/skill-consumption command evidence`).
  - contrast-2: failure remains report evidence completeness, not runtime logic.
  - fix-2: run missing triplet commands and record evidence in LAST.
  - check-3: rerun canonical verify failed at patch check with out-of-scope path `test_final.py`.
  - contrast-3: `test_final.py` is an unrelated preexisting worktree file not part of this task scope.
  - minimal next repair: remove or move `test_final.py` from worktree (or explicitly include it in scoped PLAN if intentionally part of this patch), then rerun canonical verify.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: `process_message -> detect_conversation_mode -> maybe_override_conversation_mode_with_model -> sync_project_context/build_support_prompt` 主链已连通。
  - accumulated: mode-router prompt/request/provider/result 证据累计到 support session artifacts，并写 `SUPPORT_MODE_ROUTER_APPLIED/SKIPPED` events。
  - consumed: 仲裁后 mode 被后续 prompt/context/bridge 逻辑实际消费；低置信度时回退到规则首判。

## Notes / Decisions

- Default choices made: 规则首判保留，仲裁仅在歧义 turn 触发。
- Alternatives considered: 全量改成模型首判；不采纳（风险高、抖动大、成本高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: if this fixes repeated user-visible misroute class, append one scoped issue-memory entry.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a repo-local support routing adjustment on existing workflow assets.
- persona_lab_impact: none.

## Results

- Files changed:
  - `docs/10_team_mode.md`
  - `meta/backlog/execution_queue.json`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-support-mode-router-model-assist.md`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-support-mode-router-model-assist.md`
  - `meta/run_pointers/LAST_BUNDLE.txt`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `$env:PYTHONPATH='tests'; python -m unittest -v test_support_bot_humanization.SupportBotHumanizationTests.test_model_mode_router_can_reclassify_ambiguous_turn_to_status_query test_support_bot_humanization.SupportBotHumanizationTests.test_model_mode_router_falls_back_to_detected_mode_on_low_confidence` => `0`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1` (workflow gate: LAST.md not updated)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1` (workflow gate: missing triplet evidence in LAST.md)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1` (patch check: out-of-scope path `test_final.py`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1` (closure rerun, same first failure: out-of-scope path `test_final.py`)
- Queue status update suggestion (`todo/doing/done/blocked`): blocked

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-24 | 支持对话模式二段判定（规则首判 + 模型仲裁） | [→](archive/20260324-support-mode-router-model-assist.md) |
| 2026-03-21 | src 功能边界拆分（Bridge 瘦身 + 单一文件操作适配层） | [→](archive/20260321-src-functional-boundary-refactor.md) |
| 2026-03-17 | Support frontdesk 显式状态机与任务槽位接线 | [→](archive/20260317-support-frontdesk-state-machine.md) |
| 2026-03-17 | Support 旧项目进度追问绑定真实 run 状态 | [→](archive/20260317-support-previous-project-status-grounding.md) |
| 2026-03-17 | Support greeting turn 保留主动进度基线 | [→](archive/20260317-support-proactive-baseline-preserve-on-greeting.md) |
| 2026-03-17 | Support 主动推送误复用寒暄修复 | [→](archive/20260317-support-proactive-push-greeting-dup-guard.md) |
| 2026-03-16 | Support 主动进度推送与旧大纲恢复 | [→](archive/20260316-support-proactive-progress-and-resume.md) |
| 2026-03-16 | Support 状态/进度回复绑定真实 run 进展 | [→](archive/20260316-support-status-progress-grounding.md) |
| 2026-03-16 | Support greeting 泄露旧项目/旧交付上下文硬化 | [→](archive/20260316-support-greeting-stale-context-hardening.md) |
| 2026-03-16 | Support 对话场景先分流再回复 | [→](archive/20260316-support-conversation-situation-routing.md) |

Full archive: `meta/tasks/archive/`
