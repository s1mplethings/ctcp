# Update 2026-03-12 - support bot 全部用户可见回复走模型

### Queue Binding
- Queue Item: `ADHOC-20260312-support-all-turns-model-routing`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 按产品口径统一 support bot：所有用户可见回复，包括 greeting/smalltalk，都走 `support_lead` model；`GREETING/SMALLTALK` 仍只作为路由分类，禁止进入项目规划/缺信息/权衡提问逻辑，但不再走本地固定话术 fast path。
- Scope:
  - 更新 authoritative docs 和 support prompt contract，去掉“问候 stays local”的表述。
  - 修改 `scripts/ctcp_support_bot.py`，删除正常执行路径中的 `local_smalltalk` 分支。
  - 补回归，证明 greeting turn 现在走 provider path，同时不破坏项目记忆隔离和 backend wiring。
- Out of scope:
  - bridge / dispatch / orchestrator 核心状态机
  - provider credential / model infra
  - 非 support lane 的历史归档文档清理

### Task Truth Source
- task_purpose:
  support bot 的所有正常用户可见回复都应通过模型生成；GREETING/SMALLTALK 只控制后续逻辑边界，不再决定“本地回复 vs 模型回复”。
- allowed_behavior_change:
  - `docs/00_CORE.md`
  - `docs/10_team_mode.md`
  - `agents/prompts/support_lead_reply.md`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - 不得重新打开 greeting/smalltalk 的本地固定回复 fast path。
  - 不得破坏 support bot 到 backend run 的既有 bridge wiring。
  - 不得扩大到 provider infra 或 orchestrator 语义重构。

### Integration Check
- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `docs/00_CORE.md`, `docs/10_team_mode.md`, `agents/prompts/support_lead_reply.md`, `scripts/ctcp_support_bot.py`
- downstream:
  conversation mode gate -> configured support provider -> `build_final_reply_doc()` -> `artifacts/support_reply.json`
- source_of_truth:
  support session `artifacts/support_reply.json` + `artifacts/support_session_state.json`
- fallback:
  正常路径所有回复都走模型；只有 provider unavailable / deferred / exec_failed 时才允许 customer-facing degrade 或 manual fallback
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - greeting/smalltalk normal path emitting `local_smalltalk`
  - docs still claiming “greeting stays local”
  - bypassing model for customer-visible success-path replies
- user_visible_effect:
  - greeting/smalltalk replies come from the configured support model
  - all turns share one support-lead tone system
  - project-memory isolation and backend bridge behavior remain intact

### Results
- Files changed:
  - pending
- Verification summary:
  - pending
- Skill decision:
  - skillized: no, because this is a repository-local policy/wiring refinement for the existing support lane, not a reusable multi-repo workflow asset.
