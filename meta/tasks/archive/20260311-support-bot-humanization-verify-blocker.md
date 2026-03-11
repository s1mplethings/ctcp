# Update 2026-03-11 - 收口 support-bot humanization verify blocker

### Queue Binding

- Queue item: `ADHOC-20260311-support-bot-humanization-verify-blocker`
- Scope lane: support reply shaping / frontend rendering boundary / Telegram customer-facing fallback
- Why now:
  - backend hard-local role patch 已经把 workflow gate、triplet guard、lite replay 清干净，canonical verify 的首个剩余失败点只剩 `test_support_bot_humanization.py` 的 3 个 regression。
  - 这 3 个失败都落在用户可见回复链路，必须单独绑定 scope，不能继续挂在 backend provider 任务下面静默扩展。

### Scope / Non-goals

- In scope:
  - 修复 `tools/telegram_cs_bot.py` 里的 bare project creation / new-run kickoff customer reply，让它问项目目标与期望结果，而不是回显泛化项目请求。
  - 修复 `frontend/response_composer.py` 对低信号或带 internal marker 的 raw reply 过度信任问题，让项目详情 turn 回到 frontend-reviewed PM reply。
  - 补/改最小 regression，并记录 issue memory / meta evidence。
- Out of scope:
  - 改 dispatcher/provider 选路。
  - 改 orchestrator/run artifact contract。
  - 重写 support-bot 全量文案风格或新增大规模模板系统。

### Task Truth Source (single source for current task)

- task_purpose: 收口 canonical verify 当前剩余的 support-bot humanization failures，让项目创建和项目详情回复继续遵守 CTCP 的 frontend boundary：优先当前详细需求、避免 internal marker 外泄、必要时才追问高杠杆问题。
- allowed_behavior_change:
  - `tools/telegram_cs_bot.py` 可调整项目创建 kickoff fallback / new-run local ack / customer reply shaping。
  - `frontend/response_composer.py` 可调整项目态下 raw reply 的保留条件，让低信号或 internal-marker 文本回退到 frontend-reviewed compose reply。
  - `tests/test_support_bot_humanization.py`、`tests/test_frontend_rendering_boundary.py` 可补最小 regression。
  - `ai_context/problem_registry.md` 可记录这次用户可见回复回退失真。
  - `meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录本轮证据。
- forbidden_goal_shift:
  - 不得把本轮扩成 Telegram/support-bot 全量重写。
  - 不得放宽 frontend/customer-facing boundary 去直接暴露 internal marker 或 backend raw failure。
  - 不得改 provider selection、whiteboard wiring、orchestrator state machine 来绕过当前回复问题。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `frontend/response_composer.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `tools/providers/*`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
- completion_evidence:
  - bare project creation / mojibake fallback 的用户可见回复不再只是泛化“创建项目”，而会明确请求项目目标与期望结果。
  - `support_turn_local` 在已有详细 requirement 时，不再把 `missing runtime_target` 或泛化旧问题原样吐给用户，而会走 frontend-reviewed PM reply，并优先当前详细 requirement source。
  - `test_support_bot_humanization.py`、`test_frontend_rendering_boundary.py`、triplet guard 和 canonical verify 通过。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - Telegram 绑定会话入口在 `tools/telegram_cs_bot.py::_handle_message`，会分流到 `_create_run`（新目标）或 `_send_customer_reply`（support turn）。
- Downstream consumer analysis:
  - `_send_customer_reply` 把 `raw_backend_state`、`task_summary`、`raw_reply_text` 交给 `frontend.render_frontend_output`，随后 `build_user_reply_payload` 负责最终 customer-facing 文本。
- Source of truth:
  - 项目创建 kickoff 真源：`tools/telegram_cs_bot.py::_project_kickoff_reply` / `build_employee_note_reply` / `_create_run`。
  - 项目详情 reply shaping 真源：`frontend/response_composer.py::run_internal_reply_pipeline` / `_stage_project_manager_draft`。
- Current break point / missing wiring:
  - 新目标重绑后会直接走 `_create_run` 本地 ack，当前 ack 对“我想创建一个项目”这种低信号输入只回显泛化项目请求，没有进入项目目标/期望结果的 kickoff。
  - 项目详情 turn 当前总是保留 raw model text；当 raw text 低信号或含 `missing runtime_target` 这类 internal marker 时，会覆盖 frontend-reviewed PM reply，导致旧问题与内部标记泄漏到用户面前。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: Telegram text turn -> `_handle_message` -> `_create_run` or `_send_customer_reply`.
- current_module: `tools/telegram_cs_bot.py` + `frontend/response_composer.py`.
- downstream: `build_user_reply_payload` -> Telegram public send + support session state persistence.
- source_of_truth: `tools/telegram_cs_bot.py`, `frontend/response_composer.py`, `tests/test_support_bot_humanization.py`.
- fallback: 低信号/内部标记 raw reply 只允许在 greeting/smalltalk 等显式 raw-safe 场景保留；项目创建和项目详情场景应退回 frontend-reviewed customer reply。
- acceptance_test:
  - `python -m py_compile tools/telegram_cs_bot.py frontend/response_composer.py tests/test_support_bot_humanization.py tests/test_frontend_rendering_boundary.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 只改测试期待，不改运行时代码。
  - 保留 `missing runtime_target` 之类 internal marker，再靠下游 sanitize 尝试兜底。
  - 用更强的 generic follow-up 问题替代项目详情总结，回避 requirement source 选择问题。
- user_visible_effect:
  - 项目创建 turn 会更像项目经理 kickoff，而不是只回显“我想做个项目”。
  - 详细需求 turn 会优先反映当前详细 requirement，而不是被旧历史或 internal marker 带偏。

### DoD Mapping (from request / current verify blocker)

- [x] DoD-1: bare project creation kickoff 不再回显泛化项目请求，而是请求项目目标/输入/期望结果。
- [x] DoD-2: 项目详情 turn 在低信号 raw reply 下会回到 frontend-reviewed PM reply，并优先当前详细 requirement source。
- [x] DoD-3: targeted regressions + canonical verify 清掉当前剩余失败点。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 先绑定新的 queue/CURRENT/LAST，把 support-bot humanization verify blocker 从 backend 任务里拆出来。
2) 在 `tools/telegram_cs_bot.py` 收紧 bare project creation kickoff fallback。
3) 在 `frontend/response_composer.py` 为项目态增加低信号/internal-marker raw reply 的回退条件。
4) 补最小 regression，并执行 support/frontend targeted tests、triplet guard、canonical verify。

### Notes / Decisions

- Default choices made: 先以最小运行时路径修复，不扩大到 prompt/provider/orchestrator 层。
- Alternatives considered: 只在 `build_user_reply_payload` 追加更多 post-sanitize 替换；拒绝，因为问题根因在 reply pipeline 对 raw project replies 的保留条件。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 已记录到 `ai_context/problem_registry.md` Example 5。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: yes (`ctcp-workflow` + `ctcp-gate-precheck`)。

### Results

- Files changed:
  - `tools/telegram_cs_bot.py`
  - `frontend/response_composer.py`
  - `tests/test_frontend_rendering_boundary.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/archive/20260311-support-bot-humanization-verify-blocker.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/archive/20260311-support-bot-humanization-verify-blocker.md`
  - `meta/reports/LAST.md`
- Verification summary:
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
- Queue status update suggestion (`todo/doing/done/blocked`): `done`
