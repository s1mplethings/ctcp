# Update 2026-03-11 - Telegram 新建 run 的执行 provider 对齐

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
- `docs/10_team_mode.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `tools/telegram_cs_bot.py`
- `tools/providers/api_agent.py`
- `scripts/ctcp_dispatch.py`
- `tests/test_api_agent_templates.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `tests/test_provider_selection.py`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`

### Plan
1) 查明 Telegram greeting local path 与 new-run execution path 的 provider 分叉点。
2) 在 `api_agent` 收紧 readiness 判定，拦截 placeholder key 误配置。
3) 在 Telegram `_create_run` 后对齐 run 级 dispatch_config，避免 broken `api_agent` 默认。
4) 增补 run provider alignment / api readiness 回归测试。
5) 执行 targeted tests + canonical verify，并记录首个失败点与最终结果。

### Changes
- `tools/providers/api_agent.py`
  - `OPENAI_API_KEY=ollama` 且缺少 `OPENAI_BASE_URL` 时不再判定为 external API ready。
- `tools/telegram_cs_bot.py`
  - 新增 OpenAI env 快照与 engineering API readiness helper。
  - 在 `_create_run` 后校准 run 级 `dispatch_config.json`；当外部 API env 未真正就绪时，将 Telegram-created run 对齐到 `manual_outbox`，避免 project intake 直接撞 401。
  - `new_run_created` ops_status 补充 dispatch alignment evidence。
- `tests/test_api_agent_templates.py`
  - 新增 placeholder ollama key 缺 base_url 的 readiness 回归。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 新增 Telegram-created run 会把 broken `api_agent` 配置改写为 `manual_outbox` 的回归。
- `docs/10_team_mode.md`
  - 记录 Telegram 新建 run 的 provider 校准规则。
- `ai_context/problem_registry.md`
  - 记录 greeting local path 与 project-intake api path 错位导致 401 的问题记忆。
- `meta/backlog/execution_queue.json`
  - 新增 `ADHOC-20260311-telegram-run-provider-alignment`。
- `meta/tasks/CURRENT.md`
  - 追加本轮 task truth / integration check / verify evidence。

### Verify
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

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`（Update 2026-03-11 - Telegram 新建 run 的执行 provider 对齐）
- Run-time truth:
  - `${run_dir}/artifacts/dispatch_config.json`
  - `${run_dir}/logs/telegram_cs_bot.ops.jsonl`
  - `${run_dir}/logs/plan_agent.stderr`
- Regression targets:
  - `tests/test_api_agent_templates.py`
  - `tests/test_telegram_cs_bot_employee_style.py`
  - `tests/test_provider_selection.py`

### Integration Proof
- upstream: Telegram project-intake message -> `Bot._create_run`.
- current_module: Telegram run dispatch alignment + `api_agent` readiness guard.
- downstream: `${run_dir}/artifacts/dispatch_config.json` -> `ctcp_dispatch.load_dispatch_config` / `api_agent._resolve_templates`.
- source_of_truth: run-level dispatch config plus OpenAI env/base_url values.
- fallback: external API env not ready -> Telegram-created run downgrades to `manual_outbox`; greeting/smalltalk remains local.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - local greeting path正常，但 project-intake 仍继承 broken `api_agent` 默认。
  - 用非空 key 判定 API ready，却不校验 ollama placeholder + base_url 组合。
  - 只在用户回复里解释 401，而不修 provider 选择真源。
- user_visible_effect: 用户在 Telegram 里仍能正常寒暄；真正立项时不会因为错误外部 API 默认而立即撞到 401。

