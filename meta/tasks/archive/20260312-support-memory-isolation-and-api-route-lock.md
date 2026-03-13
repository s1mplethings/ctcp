# Update 2026-03-12 - support bot 记忆隔离与显式 API 路由锁定

### Queue Binding
- Queue Item: `ADHOC-20260312-support-memory-isolation-and-api-route-lock`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 修复 support bot 现场对话里暴露出的三类串线问题: persistent project brief 被短句 follow-up 覆盖、问候漂成 provider 语言、显式 API 路由在 reply shaping 失败时跌回本地模型并产生错误语义。
- Scope:
  - `scripts/ctcp_support_bot.py` 拆 support session memory zones、改 current-turn-first routing、恢复 greeting/smalltalk local fast path、收紧显式 provider override fallback。
  - 补最小 regression，记录 issue memory 与本轮 workflow evidence。
- Out of scope:
  - `scripts/ctcp_front_bridge.py` / `scripts/ctcp_dispatch.py` bridge contract
  - provider credential / model infra
  - orchestrator state machine

### Task Truth Source
- task_purpose:
  support bot 必须把 project brief、latest turn、provider runtime state 分隔存储，避免“没有，你先做着”之类的短句覆盖项目定义；问候必须本地化；显式 API route 不得在 reply 出现乱码替换符后跌入 `ollama_agent` 造成语义漂移。
- allowed_behavior_change:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - 不得把修复退化成 prompt-only 提示。
  - 不得改 bridge / dispatch / orchestrator 核心语义。
  - 不得扩大到 provider credentials / model infra 重构。

### Integration Check
- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `scripts/ctcp_support_bot.py`
- downstream:
  isolated support session state -> provider selection or local fast path -> `build_final_reply_doc()` -> `artifacts/support_reply.json`
- source_of_truth:
  support session `artifacts/support_session_state.json` + `artifacts/support_reply.json`
- fallback:
  greeting/smalltalk stays local; explicit provider override failure degrades to manual/customer-facing reply without crossing to another semantic provider
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - one `task_summary` slot holding both persistent project brief and latest user turn
  - explicit `api_agent` silently falling through to `ollama_agent`
  - greeting depending on provider output
- user_visible_effect:
  - project brief stays stable across short follow-ups
  - greeting stays local and language-stable
  - API-only support routing does not drift into local-model semantics

### Results
- Files changed:
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260312-support-memory-isolation-and-api-route-lock.md`
- Verification summary:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (12 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (10 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => first run `1` (`LAST.md` missing first-failure/minimal-fix evidence), second run `0` after report fix
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-120504` (`passed=14 failed=0`)
- Skill decision:
  - skillized: no, because this is repository-local support-session state isolation and reply-routing refinement, not a reusable multi-repo workflow asset.
