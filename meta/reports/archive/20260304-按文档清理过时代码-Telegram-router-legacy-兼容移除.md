# Update 2026-03-04（按文档清理过时代码：Telegram router legacy 兼容移除）

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
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `scripts/contract_checks.py`
- `scripts/workflow_checks.py`
- `agents/prompts/support_lead_router.md`
- `docs/10_team_mode.md`

### Plan
1) Docs/spec-first：更新任务单，明确本次“清理过时兼容代码”范围与 DoD。  
2) Code：移除 `telegram_cs_bot` 中文档未定义的 legacy 路由兼容字段/分支。  
3) Tests：同步更新受影响测试，去除旧路由名与旧字段依赖。  
4) Verify：执行目标单测 + `scripts/verify_repo.ps1`。  
5) Report：回填本节 Readlist/Plan/Changes/Verify/Questions/Demo。  

### Changes
- `tools/telegram_cs_bot.py`
  - 移除过时路由输出字段 `route_legacy`。
  - 移除 `api_handoff` / `local_reply` 路由别名兼容分支，统一使用 `local/api/need_more_info/handoff_human`。
  - 路由 follow-up 读取统一为 `followup_question`，不再回退 `need_user_confirm`。
  - `ops_status` 中 follow-up 字段命名统一为 `followup_question`。
- `tests/test_support_bot_humanization.py`
  - 测试输入路由从 `api_handoff/local_reply` 改为 `api/local`。
  - 测试输入字段从 `need_user_confirm` 改为 `followup_question`。
  - 路由 trace 断言改为检查标准路由值。
- `tests/test_openai_external_api_wrappers.py`
  - 固定测试环境变量 `SDDAI_OPENAI_ENDPOINT_MODE=responses`，消除主机环境变量污染导致的假失败，稳定外部 API wrapper 测试。
- `meta/tasks/CURRENT.md`
  - 新增本次任务 Update 节（DoD/Acceptance）。
- `meta/reports/LAST.md`
  - 新增本节审计记录。

### Verify
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（13 passed）
- `python -m unittest discover -s tests -p "test_support_router_and_stylebank.py" -v` => exit `0`（5 passed）
- `python -m unittest discover -s tests -p "test_openai_external_api_wrappers.py" -v` => exit `0`（3 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（首次）=> exit `1`
  - first failure: `lite scenario replay` -> `S16_lite_fixer_loop_pass`
  - first failing point: `python unit tests` 内 `test_openai_external_api_wrappers` 受环境变量影响走到 `/v1/chat/completions`，与测试契约不一致
  - minimal fix: 在 `tests/test_openai_external_api_wrappers.py` 显式设置 `SDDAI_OPENAI_ENDPOINT_MODE=responses`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（修复后重跑）=> exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=31`)
  - contract checks: ok
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-202311`（`passed=14 failed=0`）
  - python unit tests: `Ran 108 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-202311/summary.json`
- First-failure replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-201448/summary.json`

