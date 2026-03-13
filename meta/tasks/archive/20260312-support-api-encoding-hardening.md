# Update 2026-03-12 - support bot API 中文回复编码修复

### Queue Binding
- Queue Item: `ADHOC-20260312-support-api-encoding-hardening`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 修复 support bot 的 API 中文回复在 Windows 下被打成 mojibake 的问题，确保 provider 产物和 Telegram 用户可见回复都保持可读中文。
- Scope:
  - 修 `tools/providers/api_agent.py` 的 child stdout/stderr 捕获与解码。
  - 给 `scripts/externals/openai_*_api.py` 加 UTF-8 stdio。
  - 给 `scripts/ctcp_support_bot.py` 补最后一层 mojibake 直出抑制。
  - 补回归、live smoke、verify 和重启证据。
- Out of scope:
  - bridge / dispatch / orchestrator 核心流程
  - API prompt 语义优化
  - provider credential 链重构

### Task Truth Source
- task_purpose:
  support bot 通过 `api_agent` 输出中文时，provider 产物和最终 Telegram 回复都必须保持可读中文，不能出现 `ãܸ˰...` / `���...` 这类乱码。
- allowed_behavior_change:
  - `tools/providers/api_agent.py`
  - `scripts/externals/openai_agent_api.py`
  - `scripts/externals/openai_plan_api.py`
  - `scripts/externals/openai_patch_api.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_support_bot_humanization.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - 不得只改 prompt 或客服文案而不修 provider 编码根因。
  - 不得重新引入本地固定回复 fast path 掩盖 API 编码问题。

### Integration Check
- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `tools/providers/api_agent.py`, `scripts/externals/openai_agent_api.py`, `scripts/externals/openai_plan_api.py`, `scripts/externals/openai_patch_api.py`, `scripts/ctcp_support_bot.py`
- downstream:
  `api_agent.execute()` -> `artifacts/support_reply.provider.json` -> `build_final_reply_doc()` -> `artifacts/support_reply.json` -> Telegram `sendMessage`
- source_of_truth:
  support session `logs/agent.stdout`, `artifacts/support_reply.provider.json`, `artifacts/support_reply.json`
- fallback:
  若 provider 文本仍像 mojibake，support bot 必须给用户可读回复，不能把脏字符串直发到 Telegram
- acceptance_test:
  - `python -m py_compile tools/providers/api_agent.py scripts/externals/openai_agent_api.py scripts/externals/openai_plan_api.py scripts/externals/openai_patch_api.py scripts/ctcp_support_bot.py tests/test_api_agent_templates.py tests/test_support_bot_humanization.py`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不修 `api_agent` 解码路径
  - 把乱码留在 `support_reply.provider.json` 里只在 Telegram 层吞掉
  - 用机械化本地答复代替 API success path
- user_visible_effect:
  - 中文 greeting / 项目回复经 API 路径返回时保持可读中文
  - 用户不再收到 mojibake

### Results
- Files changed:
  - `tools/providers/api_agent.py`
  - `scripts/externals/openai_agent_api.py`
  - `scripts/externals/openai_plan_api.py`
  - `scripts/externals/openai_patch_api.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_support_bot_humanization.py`
  - `ai_context/problem_registry.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Verification summary:
  - `python -m py_compile tools/providers/api_agent.py scripts/externals/openai_agent_api.py scripts/externals/openai_plan_api.py scripts/externals/openai_patch_api.py scripts/ctcp_support_bot.py tests/test_api_agent_templates.py tests/test_support_bot_humanization.py` => `0`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` => `0` (11 passed)
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (14 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (11 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `python scripts/workflow_checks.py` => first run `1`, second run `0` after adding explicit completion-criteria evidence
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
  - final lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-180401` (`passed=14 failed=0`)
  - direct child smoke + live support smoke + Telegram restart all completed
- Skill decision:
  - skillized: no, because this is a repository-local support provider encoding repair, not a reusable multi-repo workflow asset.
