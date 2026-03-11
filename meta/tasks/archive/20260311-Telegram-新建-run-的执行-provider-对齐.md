# Update 2026-03-11 - Telegram 新建 run 的执行 provider 对齐

### Queue Binding
- Queue Item: `ADHOC-20260311-telegram-run-provider-alignment`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 修正 Telegram bot 的项目入口流程，避免无 run 的寒暄走本地回复、但真正建项目时又因为错误的 `api_agent` 默认而立刻 401。
- Scope:
  - 在 Telegram 新建 run 后校准该 run 的工程 dispatch provider。
  - 识别 `OPENAI_API_KEY=ollama` 且无 `OPENAI_BASE_URL` 的误配置，不再把它当成外部 API 可用。
  - 补充 run 创建/provider readiness 回归。
- Out of scope:
  - 全局 workflow recipe 默认 provider 重设计。
  - 扩展 CTCP dispatcher 的角色 provider 支持矩阵。
  - 新模型/provider 接入。

### Task Truth Source (single source for current task)

- task_purpose: 让 Telegram-created run 的工程执行链与真实可用的运行时对齐，消除“寒暄可答但项目一启动就 API 401”的错位流程。
- allowed_behavior_change:
  - `tools/telegram_cs_bot.py` 可在 `_create_run` 后补 run 级别的 dispatch_config 对齐逻辑。
  - `tools/providers/api_agent.py` 可收紧 API readiness 判定，拦截 ollama placeholder key 无 base_url 的误配置。
  - `tests/test_api_agent_templates.py` 与 `tests/test_telegram_cs_bot_employee_style.py` 可新增相关回归。
  - `docs/10_team_mode.md`、`ai_context/problem_registry.md`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录新的运行约束与证据。
- forbidden_goal_shift:
  - 不得把这轮修改扩展成全局 dispatch 架构重写。
  - 不得破坏纯寒暄本地回复路径。
  - 不得继续让 Telegram-created run 在明显误配置的 API 环境下默认走 `api_agent`。
- in_scope_modules:
  - `tools/telegram_cs_bot.py`
  - `tools/providers/api_agent.py`
  - `docs/10_team_mode.md`
  - `ai_context/problem_registry.md`
  - `tests/test_api_agent_templates.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/*`
- completion_evidence:
  - Telegram-created run 在 `OPENAI_API_KEY=ollama` 且无 `OPENAI_BASE_URL` 时不再保留 `api_agent` 为执行默认。
  - `api_agent` readiness 明确拒绝上述误配置。
  - targeted tests + canonical verify 通过并记录结果。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 用户寒暄入口走 `Bot._handle_message` 的 local smalltalk 分支；项目立项入口走 `Bot._create_run` -> `ctcp_orchestrate new-run`。
- Downstream consumer analysis:
  - run 创建后真正执行链读取 `artifacts/dispatch_config.json` 并由 `ctcp_dispatch` 解析 provider。
- Source of truth:
  - run 级 provider 真源是 `${run_dir}/artifacts/dispatch_config.json`。
  - API readiness 真源是 `OPENAI_API_KEY` / `CTCP_OPENAI_API_KEY` + `OPENAI_BASE_URL` / `CTCP_OPENAI_BASE_URL`。
- Current break point / missing wiring:
  - smalltalk 本地回复与工程执行 provider 选择没有对齐；`api_agent` 对 placeholder key 的 readiness 判断过宽。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: Telegram message -> `_handle_message` -> `_create_run`.
- current_module: run-level dispatch alignment in `tools/telegram_cs_bot.py` + provider readiness guard in `tools/providers/api_agent.py`.
- downstream: run_dir `dispatch_config.json` -> `ctcp_dispatch.load_dispatch_config` / `api_agent._resolve_templates`.
- source_of_truth: `${run_dir}/artifacts/dispatch_config.json`, process env for OpenAI/API settings.
- fallback: external API env not ready -> Telegram-created run downgrades to `manual_outbox` instead of broken `api_agent`; greeting/smalltalk stays local as before.
- acceptance_test:
  - `python -m py_compile tools/providers/api_agent.py tools/telegram_cs_bot.py tests/test_api_agent_templates.py tests/test_telegram_cs_bot_employee_style.py`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 仅靠用户提示解释 API 不可用，但不修 provider 选择。
  - 继续把 `OPENAI_API_KEY=ollama` 无 base_url 当成可用外部 API。
  - 为 greeting/smalltalk 人为创造 run 来掩盖 provider 错位。
- user_visible_effect:
  - 用户仍可在第一句寒暄得到本地回复。
  - 真正建项目时不会再因为错误 API 默认而立刻遇到 401 阻塞。

### DoD Mapping (from request)

- [x] DoD-1: 查清为什么第一句能回答但下一句显示不能调用。
- [x] DoD-2: Telegram-created run 在外部 API 误配置时不再默认走 broken `api_agent`。
- [x] DoD-3: `api_agent` 明确拦截 ollama placeholder key 无 base_url 的误配置。
- [ ] DoD-4: targeted tests + canonical verify 回填到案。

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first task update included
- [x] Targeted tests pass
- [x] `scripts/verify_repo.*` passes（或记录首个失败点）
- [x] `meta/reports/LAST.md` updated in same patch

### Plan

1) 在 `api_agent` 增加误配置守卫，识别 `OPENAI_API_KEY=ollama` 且缺 base_url 的情况。
2) 在 Telegram `_create_run` 后对 run 级 dispatch_config 做 provider 对齐。
3) 补 run 创建/provider readiness 回归。
4) 执行 targeted tests + canonical verify，并把首个失败点/最终结果回填到 CURRENT/LAST。

### Notes / Decisions

- Default choices made: 不改全局 recipe 默认，只修 Telegram-created run 的 provider 对齐。
- Alternatives considered: 直接扩展 dispatcher 让所有角色都支持 `ollama_agent`；拒绝，因为会越过当前 docs/contract 的 provider 矩阵边界。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 记录“ollama placeholder key 被误判为外部 API ready”到 `ai_context/problem_registry.md`。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a repository-local runtime correction tied to current Telegram execution wiring.

### Results (2026-03-11 - Telegram 新建 run 的执行 provider 对齐)

- Files changed:
  - `tools/telegram_cs_bot.py`
  - `tools/providers/api_agent.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `docs/10_team_mode.md`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- Verification summary:
  - `python -m py_compile tools/providers/api_agent.py tools/telegram_cs_bot.py tests/test_api_agent_templates.py tests/test_telegram_cs_bot_employee_style.py` => `0`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (9 passed)
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => `0` (34 passed)
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (21 passed)
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => `0` (18 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
    - summary: profile=`code`, executed gates=`lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,triplet_guard,lite_replay,python_unit_tests`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-005125` (`passed=14 failed=0`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after CURRENT/LAST/queue sync）=> `0`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-005619` (`passed=14 failed=0`)

- Queue status update suggestion (`todo/doing/done/blocked`): `done`

