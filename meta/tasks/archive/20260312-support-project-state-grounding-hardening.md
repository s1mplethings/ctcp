# Current Task

> Archived from `meta/tasks/CURRENT.md` on 2026-03-12.

## Base Task

- Queue Item: `L0-PLAN-001`
- Topic: `markdown-contract-drift-fix`
- Status: `done` (base scope completed; subsequent updates archived)

## Active Task (latest)

- File: [`meta/tasks/archive/20260312-support-project-state-grounding-hardening.md`](20260312-support-project-state-grounding-hardening.md)
- Date: 2026-03-12
- Topic: support bot 项目记忆隔离、执行指令路由与 blocked 状态落地修复
- Status: `done`

## Queue Binding

- Queue Item: `ADHOC-20260312-support-project-state-grounding-hardening`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now?
  用户在同一个 Telegram support session 里先给出 剧情项目目标，随后补了 `window开发，然后ui可以使用qt6` 和 `你先做出第一版给我看，然后我在做调整`。实际运行里，长期项目目标被实现细节覆盖，最后一条执行指令落成 `SMALLTALK`，没有真正进入 backend bridge；同时前台还向用户承诺“会开始做第一版”，与已 `blocked` 的 backend 状态矛盾。
- Dependency check:
  - `ADHOC-20260312-support-bot-backend-bridge-wiring`: `done`
  - `ADHOC-20260312-support-memory-isolation-and-api-route-lock`: `done`
  - `ADHOC-20260312-support-all-turns-model-routing`: `doing`
  - `ADHOC-20260312-support-api-encoding-hardening`: `done`
- Scope boundary:
  - 只修 support 项目记忆隔离、conversation routing 和 blocked-state reply grounding。
  - 不改 `ctcp_front_bridge.py` / `ctcp_dispatch.py` / `ctcp_orchestrate.py` 的核心执行语义，不改 provider infra，不改 unrelated dirty worktree。

## Task Truth Source (single source for current task)

- task_purpose:
  修复 `scripts/ctcp_support_bot.py -> frontend/conversation_mode_router.py -> frontend/response_composer.py` 这条 support 项目链路里的三处缺陷：项目目标被技术约束覆盖、bound run 下执行指令误判成 `SMALLTALK`、以及 blocked backend 状态仍被前台过度承诺成“已经开始做第一版”。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py` 可新增隔离记忆区，分别保存长期项目目标、技术约束和执行指令；可调整 project-brief refresh 规则与 bound-run directive 的 mode coercion。
  - `frontend/conversation_mode_router.py` 可补 active-run execution-followup 路由规则。
  - `frontend/response_composer.py` 可阻止 blocked / waiting backend 状态继续保留 optimistic raw provider reply，并让 status query 消费真实 visible state。
  - `tests/test_support_bot_humanization.py`、`tests/test_runtime_wiring_contract.py` 可补最小 regression。
  - `ai_context/problem_registry.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录问题与证据。
- forbidden_goal_shift:
  - 不得把这次修复扩大成 frontend 全面重构或 support prompt 改写任务。
  - 不得绕过 backend truth source，继续让前台靠 chat 记忆发明执行状态。
  - 不得只靠提示词或文案改写解决 routing / memory / blocked-state wiring defect。
- in_scope_modules:
  - `scripts/ctcp_support_bot.py`
  - `frontend/conversation_mode_router.py`
  - `frontend/response_composer.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `tools/providers/api_agent.py`
  - `tools/providers/ollama_agent.py`
  - 与 support 项目状态落地无关的其他未提交工作树改动
- completion_evidence:
  - 技术约束消息不再覆盖长期 `project_brief`，而是写入独立约束记忆区。
  - bound run 下 `先做第一版` / `后面我再调整` 这类执行指令不再掉成 `SMALLTALK`，并继续走 backend bridge。
  - blocked / waiting backend 状态的用户回复不再保留“已经开始做第一版”这类 optimistic raw provider wording。
  - targeted regressions、triplet guard、workflow gate、canonical verify 都留下证据，并显式满足 `connected + accumulated + consumed`。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户入口是 `scripts/ctcp_support_bot.py::process_message`。
- Downstream consumer analysis:
  - `process_message()` 先做 `detect_conversation_mode()` 和 `sync_project_context()`，项目型 turn 通过 `ctcp_front_bridge` 记录/推进 run，再把 provider 输出交给 `build_final_reply_doc()` -> `frontend/response_composer.py` 形成用户可见回复。
- Source of truth:
  - support session `artifacts/support_session_state.json`
  - bound run `RUN.json`
  - bound run `artifacts/support_whiteboard.json`
  - customer-visible `artifacts/support_reply.json`
- Current break point / missing wiring:
  - `should_refresh_project_brief()` 过于宽松，`window开发，然后ui可以使用qt6` 被写成新的长期项目摘要。
  - `route_conversation_mode()` 只在有“有效 task summary”时才把 follow-up 保在项目路由上，因此 bound run + 弱摘要 + 执行指令会掉成 `SMALLTALK`。
  - `_stage_project_manager_draft()` 在 `BLOCKED_NEEDS_INPUT / WAITING_FOR_DECISION` 下仍可能保留 raw provider 的 optimistic first-draft promise。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `scripts/ctcp_support_bot.py`, `frontend/conversation_mode_router.py`, `frontend/response_composer.py`
- downstream:
  `process_message()` -> `sync_project_context()` -> `ctcp_front_bridge` runtime helpers -> `build_final_reply_doc()` -> `render_frontend_output()` -> `artifacts/support_reply.json`
- source_of_truth:
  `artifacts/support_session_state.json`, bound run `RUN.json`, bound run `artifacts/support_whiteboard.json`, `artifacts/support_reply.json`
- fallback:
  若 backend 仍 blocked / waiting，前台只能给出 customer-facing grounded reply，不能谎称已开始制作；若执行指令无法判定，仍需优先保留 bound run 的 project path，而不是退到 `SMALLTALK`
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py frontend/conversation_mode_router.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 继续让技术约束文本直接覆盖 `project_brief`
  - 让 bound run 的执行指令掉回 `SMALLTALK`，不进 bridge
  - 在 blocked backend 状态下继续保留 raw provider 的“开始做第一版”表述
- user_visible_effect:
  - 用户补平台/框架偏好时，bot 还记得项目真正要做什么。
  - 用户说“先出第一版”时，会继续走项目推进，而不是只聊客服话术。
  - 用户不会再看到“已经开始做第一版”这类与 blocked backend 不一致的承诺。

## Results

- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `frontend/conversation_mode_router.py`
  - `frontend/response_composer.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py frontend/conversation_mode_router.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (16 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (12 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => first run `1`
    - first failure point: `meta/reports/LAST.md` missing mandatory workflow evidence (`first failure point evidence`, `minimal fix strategy evidence`)
    - minimal fix strategy: add the missing workflow evidence lines to `meta/reports/LAST.md`, then rerun `python scripts/workflow_checks.py`
  - `python scripts/workflow_checks.py` => second run `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite, workflow_gate, plan_check, patch_check, behavior_catalog_check, contract_checks, doc_index_check, triplet_guard, lite_replay, python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-193724` (`passed=14 failed=0`)

## Notes / Decisions

- Issue memory decision:
  - 记录“项目目标被技术约束覆盖 + bound run directive 落成 SMALLTALK + blocked 状态误承诺”的新 issue-memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`):
  - skillized: no, because this is a repository-local support state-grounding repair, not a reusable multi-repo workflow asset.
