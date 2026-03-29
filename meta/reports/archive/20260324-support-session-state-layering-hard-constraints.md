# Demo Report - LAST

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260324-support-session-state-layering-hard-constraints.md`](archive/20260324-support-session-state-layering-hard-constraints.md)
- Date: 2026-03-24
- Topic: Support 会话单主线状态、历史分层与阶段推进硬约束落地

### Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_frontdesk_state_machine.py`

### Plan

1. 绑定新 ADHOC 任务并固定 scope。
2. 在 support session state 增加 `active_*` 真值与 `history_layers` 四层结构。
3. 增加每轮 message intent 分类与 active stage 映射，确保插话默认回主线。
4. 让 prompt 优先消费 `working_memory + task_summary + recent_raw_turns`。
5. 跑 focused tests + canonical verify，并更新任务/报告闭环。

### Changes

- `docs/10_team_mode.md`
  - 补充单主任务真值字段、四层历史结构和 message intent 分类的 support lane 强制条款。
- `scripts/ctcp_support_bot.py`
  - `default_support_session_state` 升级为 `ctcp-support-session-state-v7`，新增 `active_task_id/active_run_id/active_goal/active_stage/active_blocker/active_next_action/latest_message_intent`。
  - 新增 `history_layers` 四层结构：`raw_turns`、`working_memory`、`task_summary`、`user_preferences`。
  - 新增 `sync_active_task_truth()`，按每轮输入/上下文持久化单主任务真值、message intent（`continue|clarify|constraint_update|new_task|small_talk|status_check`）和阶段状态。
  - `build_support_prompt()` 注入 `history_layers`，并默认使用层化记忆 + 最近有限 raw turns，而非全量历史。
  - proactive job 发送路径同步更新 active truth，避免状态层脱节。
  - `build_progress_binding()` 增加 `active_stage/stage_reason/stage_exit_condition`。
- `tests/test_support_bot_humanization.py`
  - 新增默认 schema/层化历史字段与 smalltalk 不切主线测试。
  - 新增/调整 stage 字段断言。
- `tests/test_runtime_wiring_contract.py`
  - 扩展 process_message 持久化断言：`active_*`、`latest_message_intent`、`history_layers` 已落盘。
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-support-session-state-layering-hard-constraints.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260324-support-session-state-layering-hard-constraints.md`

### Verify

- `python -m unittest discover -s tests -p "test_frontdesk_state_machine.py" -v` -> `0` (6 tests)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0` (51 tests)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (21 tests)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 tests; from canonical verify run)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 tests; from canonical verify run)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point observed during this task:
  - `workflow gate (workflow checks)` 报 `LAST.md missing mandatory workflow evidence (triplet issue memory/skill consumption command evidence)`。
- minimal fix strategy applied:
  - 在 `meta/reports/LAST.md` 补全 `test_issue_memory_accumulation_contract.py` 与 `test_skill_consumption_contract.py` 命令证据，并重跑 canonical verify；同时保留 local fix-loop 对 `build_progress_binding` FINALIZE 判定的收紧修复。

### Questions

- None.

### Demo

- 会话状态现在可直接看到单主任务六元组：`active_task_id/active_run_id/active_goal/active_stage/active_blocker/active_next_action`。
- 每轮输入被分类为 `continue|clarify|constraint_update|new_task|small_talk|status_check`，smalltalk/status 默认不覆盖主任务目标。
- prompt 上下文新增 `history_layers`，默认读 `working_memory + task_summary + recent_raw_turns`，不再把全量 raw 历史当唯一上下文。

### Integration Proof

- upstream: `process_message` / Telegram proactive cycle
- current_module: `support_session_state` schema + prompt assembly + active truth synchronizer
- downstream: customer-facing reply continuity, proactive update consistency, and runtime wiring contract checks
- source_of_truth: bound run status + support session `active_*` + layered memory state
- final lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260324-204018` (`passed=14`, `failed=0`)
