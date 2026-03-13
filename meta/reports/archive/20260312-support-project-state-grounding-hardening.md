# Demo Report - LAST

> Archived from `meta/reports/LAST.md` on 2026-03-12.

## Latest Report

- File: [`meta/reports/archive/20260312-support-project-state-grounding-hardening.md`](20260312-support-project-state-grounding-hardening.md)
- Date: 2026-03-12
- Topic: support bot 项目记忆隔离、执行指令路由与 blocked 状态落地修复

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/10_team_mode.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `frontend/conversation_mode_router.py`
- `frontend/response_composer.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

### Plan
1) 绑定 `support-project-state-grounding-hardening` task，并把 integration proof 锁到 support memory/routing/reply-grounding 链路。
2) 把长期项目目标、技术约束和执行指令拆到独立记忆区，收紧 `project_brief` refresh。
3) 给 active-run follow-up 加 project 路由守卫，避免 `先出第一版` 类消息落回 `SMALLTALK`。
4) 禁止 blocked / waiting backend 状态继续保留 optimistic raw provider promise。
5) 跑 targeted regressions、triplet、workflow、canonical verify，并把 issue-memory 与报告闭环补齐。

### Changes
- `scripts/ctcp_support_bot.py`
  - added isolated memory zones for long-term project constraints and user execution directives
  - tightened `should_refresh_project_brief()` so implementation-detail turns no longer replace the long-term project goal
  - added bound-run execution-directive coercion so `先做第一版` style turns stay on the project path
  - injected separated memory fields and active-task binding into support prompt / frontend render notes
- `frontend/conversation_mode_router.py`
  - added active project binding detection and execution-followup routing so a bound run can keep project follow-ups on `PROJECT_DETAIL` even when the current summary is weak
- `frontend/response_composer.py`
  - prevented execution-directive text from replacing an already valid project summary
  - forced state-grounded reply generation for blocked / decision-needed backend states instead of preserving optimistic raw provider text
  - made status-query rendering consume real backend visible state
- `tests/test_support_bot_humanization.py`
  - added regression for separated goal/constraint/directive memory zones
  - added regression proving blocked backend state rewrites “会开始做第一版” style overpromises
- `tests/test_runtime_wiring_contract.py`
  - added regression proving a bound run keeps execution directives on the project route even if the summary only contains technical constraints

### Verify
- `python -m py_compile scripts/ctcp_support_bot.py frontend/conversation_mode_router.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (16 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (12 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `python scripts/workflow_checks.py` => first run `1`
- first failure point:
  - `meta/reports/LAST.md` was missing mandatory workflow evidence (`first failure point evidence`, `minimal fix strategy evidence`)
- minimal fix strategy:
  - add the missing workflow evidence lines to `meta/reports/LAST.md`, rerun `python scripts/workflow_checks.py`, then continue to canonical verify
- `python scripts/workflow_checks.py` => second run `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
  - summary: profile=`code`, executed gates=`lite, workflow_gate, plan_check, patch_check, behavior_catalog_check, contract_checks, doc_index_check, triplet_guard, lite_replay, python_unit_tests`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-193724` (`passed=14 failed=0`)
- `git diff --stat -- frontend/conversation_mode_router.py frontend/response_composer.py scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py ai_context/problem_registry.md meta/backlog/execution_queue.json meta/tasks/CURRENT.md meta/reports/LAST.md meta/tasks/archive/20260312-support-project-state-grounding-hardening.md meta/reports/archive/20260312-support-project-state-grounding-hardening.md` => `0`

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`
- Task archive: `meta/tasks/archive/20260312-support-project-state-grounding-hardening.md`
- Report archive: `meta/reports/archive/20260312-support-project-state-grounding-hardening.md`
- live repro source:
  - support session `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/6092527664`
  - bound run `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/20260312-082001-341910-orchestrate`

### Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `scripts/ctcp_support_bot.py`, `frontend/conversation_mode_router.py`, `frontend/response_composer.py`
- downstream: `process_message()` -> `sync_project_context()` -> `ctcp_front_bridge` helpers -> `build_final_reply_doc()` -> `render_frontend_output()` -> `artifacts/support_reply.json`
- source_of_truth: `artifacts/support_session_state.json`, bound run `RUN.json`, bound run `artifacts/support_whiteboard.json`, `artifacts/support_reply.json`
- fallback: blocked / waiting backend states must degrade to customer-facing grounded replies, not raw optimistic promises
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py frontend/conversation_mode_router.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
