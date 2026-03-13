# Update 2026-03-12 - support bot 接入 front bridge / shared whiteboard / librarian 后台流

### Queue Binding
- Queue Item: `ADHOC-20260312-support-bot-backend-bridge-wiring`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 让 `scripts/ctcp_support_bot.py` 从 provider-only 客服壳升级为 bridge-safe 前门，在项目型 turn 上创建/绑定/推进真实 CTCP run，并消费 shared whiteboard / librarian 上下文。
- Scope:
  - `scripts/ctcp_support_bot.py` 增加 conversation-mode routing、support session -> run binding、bridge context 注入与 reply shaping。
  - `scripts/ctcp_front_bridge.py` 增加 support entry 所需的 context/mutation helper。
  - `scripts/ctcp_dispatch.py` 暴露最小 shared whiteboard helper 供 bridge 复用。
  - 补最小 regression，更新 team-mode lane doc 与 issue memory。
- Out of scope:
  - `scripts/ctcp_orchestrate.py` 核心状态机语义
  - provider credential / model 路径
  - 新并行 frontend execution path

### Task Truth Source
- task_purpose:
  support bot 的项目型消息必须经 `scripts/ctcp_front_bridge.py` 进入真实后台 run，并消费绑定 run 的 `artifacts/support_whiteboard.json` / librarian context / run status。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `docs/10_team_mode.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - 不得让 support bot 绕过 `ctcp_front_bridge` 直接改写 project run state。
  - 不得只改 prompt 文案来伪装 wiring 完成。
  - 不得引入 support 专用执行状态机。

### Integration Check
- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, `scripts/ctcp_dispatch.py`
- downstream:
  `ctcp_front_bridge` -> bound run artifacts / support whiteboard -> provider prompt -> `support_reply.json`
- source_of_truth:
  support session `artifacts/support_session_state.json` + bound run `RUN.json` / `artifacts/verify_report.json` / `artifacts/support_whiteboard.json`
- fallback:
  非项目型消息继续本地客服路径；bridge/provider 失败时降级为 customer-facing reply，不泄露 raw backend errors
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py scripts/ctcp_front_bridge.py scripts/ctcp_dispatch.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `python scripts\ctcp_support_bot.py --stdin --chat-id live_bridge_smoke_en --provider ollama_agent`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - support prompt 里声称“已接上后台”但没有绑定 run
  - 直接写 run state 绕过 bridge
  - shared whiteboard/librarian 仍只留在生产 dispatch 路径
- user_visible_effect:
  - 项目型消息会进入真实后台 run
  - customer-facing reply 会反映 run status / decisions / whiteboard context
  - 非项目型消息仍保持自然客服口吻

### Results
- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_dispatch.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `docs/10_team_mode.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py scripts/ctcp_front_bridge.py scripts/ctcp_dispatch.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (9 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (9 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => `0`
  - live smoke: `python scripts\ctcp_support_bot.py --stdin --chat-id live_bridge_smoke_en --provider ollama_agent` => `0`
    - evidence: support session state 绑定 `run_id=20260312-011651-236563-orchestrate`，support prompt 注入 bound run status 与 shared whiteboard snapshot
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-012536` (`passed=14 failed=0`)
- Skill decision:
  - skillized: no, because this is repository-local support-entry runtime wiring refinement, not a stable reusable multi-repo workflow asset.
