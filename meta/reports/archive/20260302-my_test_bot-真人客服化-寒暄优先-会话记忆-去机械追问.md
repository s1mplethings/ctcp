# Update 2026-03-02 (my_test_bot 真人客服化：寒暄优先 + 会话记忆 + 去机械追问)

### Goal
- 按用户要求把 `my_test_bot` 调整成更像真人客服：
  - 支持日常寒暄，不走工程化话术
  - 具备跨轮记忆
  - 降低“想到什么说什么”与重复追问

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `docs/00_CORE.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/TEMPLATE.md`
- `meta/tasks/CURRENT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `docs/10_team_mode.md`

### Research-first (online)
- Research log: `meta/externals/20260302-telegram-cs-human-memory.md`
- Sources:
  - Rasa slots memory: https://rasa.com/docs/reference/primitives/slots
  - AWS Lex session attributes: https://docs.aws.amazon.com/lexv2/latest/dg/context-mgmt-session-attribs.html
  - Dialogflow small talk: https://cloud.google.com/dialogflow/es/docs/small-talk
  - Bot Framework state: https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-concept-state?view=azure-bot-service-4.0

### Plan
1) Docs/spec first：更新 `meta/tasks/CURRENT.md` 与 `docs/10_team_mode.md`，记录本次目标与行为约束。  
2) Code：在 `tools/telegram_cs_bot.py` 增加寒暄优先路径、slot-like memory、追问去重。  
3) Tests：增加最小测试覆盖新行为，确保不回归现有客服人性化测试。  
4) Verify：执行 `scripts/verify_repo.ps1` 唯一验收入口并记录证据。  
5) Report：回填本节到 `meta/reports/LAST.md`。  

### Changes
- `meta/externals/20260302-telegram-cs-human-memory.md`
  - 新增外部调研记录，明确采用“结构化会话记忆 + 小聊优先 + 单问题澄清”的实现策略。
- `docs/10_team_mode.md`
  - 增补客服行为约束：slot-like 会话记忆、纯寒暄优先本地回复、关键追问去重。
- `meta/tasks/CURRENT.md`
  - 新增本次任务 update（DoD/Acceptance 全量落盘）。
- `tools/telegram_cs_bot.py`
  - 扩展 `support_session_state.json`：新增 `memory_slots`（`customer_name/preferred_style/current_topic/last_request`）。
  - 新增槽位提取逻辑（从用户文本抽取称呼、回复偏好、当前主题、最近诉求）。
  - 新增 `is_smalltalk_only_message`，在绑定会话中对纯寒暄走 fast path，不再默认触发工程路由问句。
  - `smalltalk_reply` 支持基于会话记忆回显上下文（例如“我记得你在推进 xxx”）。
  - 调整 router fallback 追问：去掉“patch 路径推进”工程口吻，改为客服自然澄清。
  - `_send_customer_reply` 增加重复追问去重：与 `open_questions` 相同的问题不重复发送。
  - `_normalize_next_question` 增加工程词过滤（patch/verify/run_dir/outbox/trace 等）避免技术术语直出给客户。
- `tests/test_support_bot_humanization.py`
  - 新增 `test_smalltalk_fast_path_prefers_human_reply_and_uses_memory`。
  - 新增 `test_send_customer_reply_dedupes_repeated_question`。
  - 新增 `test_support_state_updates_memory_slots_from_user_text`。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py tests/test_support_bot_humanization.py tests/test_telegram_cs_bot_employee_style.py` => exit `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（6 passed）
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（14 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=12`)
  - contract checks: ok
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-233914`（`passed=14 failed=0`）
  - python unit tests: `Ran 93 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Research: `meta/externals/20260302-telegram-cs-human-memory.md`
- Key implementation: `tools/telegram_cs_bot.py`
- Added tests: `tests/test_support_bot_humanization.py`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-233914/summary.json`

