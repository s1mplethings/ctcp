# Demo Report - LAST

> **用法**：本文件保留最近一次报告指针，同时内嵌 workflow gate 所需的最新报告摘要。
> 历史报告正文在 `meta/reports/archive/`。

## Latest Report

- File: [`meta/reports/archive/20260311-support-bot-humanization-verify-blocker.md`](archive/20260311-support-bot-humanization-verify-blocker.md)
- Date: 2026-03-11
- Topic: 收口 support-bot humanization verify blocker

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `tools/telegram_cs_bot.py`
- `frontend/response_composer.py`
- `frontend/conversation_mode_router.py`
- `frontend/project_manager_mode.py`
- `frontend/missing_info_rewriter.py`
- `frontend/message_sanitizer.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_frontend_rendering_boundary.py`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`

### Plan
1) 绑定新的 support-bot verify-blocker 任务，避免继续静默扩展 backend provider 任务。
2) 修复 bare project creation/new-run kickoff 的低信号回复。
3) 修复 frontend project reply pipeline 对低信号/internal-marker raw text 的保留条件。
4) 跑 targeted tests、triplet guard、canonical verify，并回填证据。

### Changes
- `tools/telegram_cs_bot.py`
  - bare project creation/new-run kickoff 现在会直接请求项目目标、输入和期望结果。
- `frontend/response_composer.py`
  - 项目态 reply pipeline 现在会在 raw reply 低信号或带 `missing <field>` internal marker 时回退到 frontend-reviewed PM reply。
- `tests/test_frontend_rendering_boundary.py`
  - 新增 low-signal raw project reply regression，直接锁住 frontend fallback 行为。
- `ai_context/problem_registry.md`
  - 记录 support-bot 用户可见回复回退失真的 issue-memory 条目。
- `meta/backlog/execution_queue.json`
  - 收口 `ADHOC-20260311-support-bot-humanization-verify-blocker` 为 `done`，并把前序 backend item 从 `blocked` 收回 `done`。
- `meta/tasks/CURRENT.md`
  - 切到本轮 task truth，并回填完成态验证证据。
- `meta/reports/archive/20260311-support-bot-humanization-verify-blocker.md`
  - 记录本轮完整 readlist/plan/verify/demo。
- `meta/reports/LAST.md`
  - 回填最新 gate-readable report summary。

### Verify
- initial blocker:
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `1`
  - first failure point: project kickoff + project detail reply shaping regressions
  - minimal fix strategy:
    - tighten bare project creation kickoff fallback in `tools/telegram_cs_bot.py`
    - stop preserving low-signal/internal-marker raw project replies in `frontend/response_composer.py`
- `python scripts/workflow_checks.py` => `0`
- `python -m py_compile tools/telegram_cs_bot.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_frontend_rendering_boundary.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (22 passed)
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (26 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
  - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-153736` (`passed=14 failed=0`)
  - python unit tests summary: `210 passed, 3 skipped`

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`
- Task archive: `meta/tasks/archive/20260311-support-bot-humanization-verify-blocker.md`
- Runtime focus:
  - `tools/telegram_cs_bot.py::_handle_message`
  - `tools/telegram_cs_bot.py::_create_run`
  - `tools/telegram_cs_bot.py::_send_customer_reply`
  - `frontend/response_composer.py::run_internal_reply_pipeline`

### Integration Proof
- upstream: Telegram text turn -> `_handle_message` -> `_create_run` or `_send_customer_reply`
- current_module: `tools/telegram_cs_bot.py` + `frontend/response_composer.py`
- downstream: `build_user_reply_payload()` -> Telegram customer-facing send + support session state writeback
- source_of_truth: `tools/telegram_cs_bot.py`, `frontend/response_composer.py`, `tests/test_support_bot_humanization.py`
- fallback: low-signal/internal-marker raw project replies should only survive in explicit raw-safe paths; otherwise frontend-reviewed PM reply is authoritative
- acceptance_test:
  - `python -m py_compile tools/telegram_cs_bot.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_frontend_rendering_boundary.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 只改测试，不改 reply pipeline。
  - 保留 internal marker 再依赖末端 sanitize 碰运气。
  - 用泛化旧问题追问替代当前详细 requirement 总结。
- user_visible_effect: bare project creation 会回到项目 kickoff 语境，详细项目 turn 会优先总结当前需求而不是回吐内部标记。

## Archive Index (recent 10)

| Date | Topic | File |
|------|-------|------|
| 2026-03-11 | 收口 support-bot humanization verify blocker | [→](archive/20260311-support-bot-humanization-verify-blocker.md) |
| 2026-03-11 | 后端角色分工收紧与本地 Librarian 硬边界 | [→](archive/20260311-backend-role-boundary-local-librarian.md) |
| 2026-03-11 | 前端 MD 范围验证（能力询问本地答复） | [→](archive/20260311-前端-MD-范围验证-能力询问本地答复.md) |
| 2026-03-11 | 设计目标改为机械层定边界 agent 定表述 | [→](archive/20260311-设计目标改为机械层定表述.md) |
| 2026-03-11 | Telegram 新建 run 的执行 provider 对齐 | [→](archive/20260311-Telegram-新建-run-的执行-provider-对齐.md) |
| 2026-03-10 | 客服用户可见通知去机械化统一闸门 | [→](archive/20260310-客服用户可见通知去机械化统一闸门.md) |
| 2026-03-10 | 客服+生产 Agent 共享白板与 Librarian 协同 | [→](archive/20260310-客服生产Agent共享白板与Librarian协同.md) |
| 2026-03-10 | 客服与项目设计流程接线 librarian 白板 | [→](archive/20260310-客服与项目设计流程接线-librarian-白板.md) |
| 2026-03-10 | Markdown 对象状态机治理基线 | [→](archive/20260310-Markdown-对象状态机治理基线-6-file-baseline.md) |
| 2026-03-09 | Frontend control plane + bridge Phase 1-2 | [→](archive/20260309-Frontend-control-plane-single-CTCP-bridge-Phase-1-2.md) |

Full archive: `meta/reports/archive/` (63 files)
