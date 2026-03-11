# Update 2026-03-03 (CTCP 2.7.0 客服 bot：local-first router + stylebank + session memory 对齐)

### Readlist
- `docs/00_CORE.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `meta/tasks/CURRENT.md`
- `agents/prompts/support_lead_router.md`
- `agents/prompts/support_lead_reply.md`
- `tools/telegram_cs_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_telegram_cs_bot_employee_style.py`
- `docs/10_team_mode.md`

### Plan
1) Docs/spec-first: 更新任务单与团队文档，先落路由与交付约束。  
2) Prompt 契约：升级 router/reply prompt 到 local-first + 2-4 段自然表达。  
3) 代码实现：在 `telegram_cs_bot` 接入新 route 枚举、StyleBank、会话状态字段与优雅降级。  
4) 测试：新增 router/stylebank 测试并回归现有客服测试。  
5) Verify：执行唯一验收入口 `scripts/verify_repo.ps1`。  
6) Report：落盘本节 Readlist/Plan/Changes/Verify/Questions/Demo。  

### Changes
- `agents/prompts/support_lead_router.md`
  - 升级为严格 JSON 路由契约：`route/intent/confidence/followup_question/style_seed/risk_flags`，并定义 `local/api/need_more_info/handoff_human`。
- `agents/prompts/support_lead_reply.md`
  - 升级为 2-4 段自然表达约束，引入 `style_seed` 变体入口，禁止列表和报告式标签。
- `tools/stylebank.py`（新增）
  - 新增确定性变体算法：`sha256(chat_id|intent|turn_index|style_seed)`。
  - 提供 `choose_variants` 与 `choose_variants_from_state`。
- `tools/telegram_cs_bot.py`
  - router 输出兼容升级：支持新 route 枚举并保留 `route_legacy` 兼容字段。
  - 统一 follow-up 字段：`followup_question`（兼容 `need_user_confirm`）。
  - `need_more_info` 路由支持“一次关键问题 + 默认继续处理”降级回复。
  - 会话状态新增并持久化：`last_intent`、`last_style_seed`（兼容旧 `style_seed`）。
  - 接入 `tools/stylebank.py`，按 route/state 生成可回放的风格变体。
  - 强化用户输出断言：无列表、至少分段、最多一个问题、内部痕迹继续过滤。
- `tests/test_support_router_and_stylebank.py`（新增）
  - 覆盖 StyleBank 确定性、router api/local 路由判定、用户输出清洁与分段断言。
- `docs/10_team_mode.md`
  - 更新客服路由/升级规则与查看进度口径说明，强调用户通道不暴露内部 key/path/trace。
- `meta/tasks/CURRENT.md`
  - 新增本次任务 Update（DoD/Acceptance）。
- `meta/reports/LAST.md`
  - 新增本节审计记录。

### Verify
- `python scripts/workflow_checks.py` => exit `0`
- `python -m unittest discover -s tests -p "test_support_router_and_stylebank.py" -v` => exit `0`（4 passed）
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（10 passed）
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（14 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - plan check: ok
  - patch check: ok (`changed_files=14`)
  - contract checks: ok
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-172520`（`passed=14 failed=0`）
  - python unit tests: `Ran 101 tests, OK (skipped=3)`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after report update）=> exit `0`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-173034`（`passed=14 failed=0`）
  - python unit tests: `Ran 101 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Task: `meta/tasks/CURRENT.md`
- Report: `meta/reports/LAST.md`
- Router prompt: `agents/prompts/support_lead_router.md`
- Reply prompt: `agents/prompts/support_lead_reply.md`
- StyleBank: `tools/stylebank.py`
- Bot implementation: `tools/telegram_cs_bot.py`
- Added tests: `tests/test_support_router_and_stylebank.py`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-172520/summary.json`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260303-173034/summary.json`

