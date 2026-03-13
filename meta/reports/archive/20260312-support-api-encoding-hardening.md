# Update 2026-03-12 - support bot API 中文回复编码修复

### Queue Binding
- Queue Item: `ADHOC-20260312-support-api-encoding-hardening`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 修复 `api_agent` 路径下 support bot 中文回复在 Windows 子进程 stdout/stdio 编码链上的损坏。
- Scope:
  - `tools/providers/api_agent.py`
  - `scripts/externals/openai_agent_api.py`
  - `scripts/externals/openai_plan_api.py`
  - `scripts/externals/openai_patch_api.py`
  - `scripts/ctcp_support_bot.py`
  - targeted regressions / issue memory / report artifacts
- Out of scope:
  - bridge / dispatch / orchestrator state machine
  - API prompt 语义重写

### Task Truth Source
- task_purpose:
  support bot 经 `api_agent` 走模型返回中文时，provider 产物与用户可见回复都必须保持可读中文。
- allowed_behavior_change:
  - provider subprocess encoding / decoding
  - wrapper stdio defaults
  - support public reply mojibake suppression
  - regression tests and issue memory
- forbidden_goal_shift:
  - 不得只靠 prompt 或表层文案遮住乱码
  - 不得用本地固定客服回复取代模型路径

### Integration Check
- upstream:
  `scripts/ctcp_support_bot.py::process_message`
- current_module:
  `tools/providers/api_agent.py`, `scripts/externals/openai_agent_api.py`, `scripts/externals/openai_plan_api.py`, `scripts/externals/openai_patch_api.py`, `scripts/ctcp_support_bot.py`
- downstream:
  `api_agent.execute()` -> `artifacts/support_reply.provider.json` -> `build_final_reply_doc()` -> `artifacts/support_reply.json` -> Telegram
- source_of_truth:
  support session logs/artifacts
- fallback:
  provider 文本若仍像 mojibake，support bot 需 customer-facing degrade
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
  - Telegram send layer swallowing乱码 while provider artifacts stay corrupt
  - local scripted success-path reply
- user_visible_effect:
  - 中文 reply 可读，乱码不再直达用户

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
  - direct child smoke returned UTF-8 Chinese
  - live support smoke returned readable Chinese for `你好`
  - Telegram bot restarted: old PID `34744`, new PID `40592`
- Skill decision:
  - skillized: no, because this is a repository-local support-provider encoding repair, not a reusable multi-repo workflow asset.
