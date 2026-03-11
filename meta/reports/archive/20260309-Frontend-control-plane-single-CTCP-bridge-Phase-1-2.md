# Update 2026-03-09 - Frontend control plane + single CTCP bridge (Phase 1-2)

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
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `docs/10_team_mode.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`
- `frontend/conversation_mode_router.py`
- `frontend/project_manager_mode.py`
- `frontend/response_composer.py`
- `frontend/message_sanitizer.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_front_api.py`
- `tools/telegram_cs_bot.py`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_telegram_cs_bot_employee_style.py`

### Plan
1) 先绑定本轮 ADHOC queue 与 CURRENT task truth 字段，完成 integration check。
2) 保持 text-first PM pipeline 结构不拆散，聚焦执行路径收敛：将 `telegram_cs_bot` 的 `new-run/status/advance/decision/upload/report` 接入 `ctcp_front_bridge`。
3) 补 bridge enforcement 回归测试，覆盖 create/status/advance + decision write。
4) 执行本地 check/fix loop（frontend + support + triplet guard）。
5) 运行 canonical verify，记录首个失败点与最小修复策略。

### Changes
- `meta/backlog/execution_queue.json`
  - 新增 `ADHOC-20260309-frontend-control-plane-single-bridge` 队列项（DoD、产物、测试清单）。
- `meta/tasks/CURRENT.md`
  - 追加本轮 Queue Binding / Task Truth / Analysis / Integration Check / Plan / Results。
- `tools/telegram_cs_bot.py`
  - 删除 direct subprocess orchestrate 主路径，`_run_orchestrate` 改为 bridge adapter（`ctcp_new_run` / `ctcp_advance` / `ctcp_get_status`）。
  - `_run_status` 优先走 `ctcp_get_status`。
  - `_collect_prompts` 增加 `ctcp_list_decisions_needed` 查询路径并保留 outbox fallback。
  - `_write_reply` 改为 `ctcp_submit_decision`（文本）/`ctcp_upload_artifact`（文件）写入。
  - `_send_verify` 通过 `ctcp_get_last_report` 获取 verify artifact path。
- `tests/test_runtime_wiring_contract.py`
  - 新增 telegram bridge wiring 回归：
    - new-run/advance 经 bridge 调用
    - status 查询经 bridge 调用
    - decision 写入经 bridge submit 调用

### Verify
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => exit `0` (8 passed)
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` => exit `0` (15 passed)
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0` (20 passed)
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0` (22 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => exit `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => exit `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - first failure point: `lite scenario replay`
  - first failing check: `S16_lite_fixer_loop_pass` step 6 (`expect_exit mismatch, rc=1, expect=0`)
  - failure chain:
    - trigger: replay suite executes fixer-loop scenario after applying `lite_fix_remove_bad_readme_link.patch`
    - failing gate: lite replay
    - failing check: second `ctcp_orchestrate.py advance --max-steps 16` remains non-zero
    - consequence: canonical verify fails at replay gate
  - evidence paths:
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/summary.json`
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/S16_lite_fixer_loop_pass/TRACE.md`
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260309-225449/S16_lite_fixer_loop_pass/sandbox/20260309-225622-687595-orchestrate/artifacts/verify_report.json`
  - minimal fix strategy (first failure only):
    - 更新 `S16` 使用的修复 patch fixture 及对应断言样本，使其与当前 frontend reply 文本基线（`B01-B06/U26`）一致。

### Questions
- None.

### Demo
- Current task card: `meta/tasks/CURRENT.md`
- Current report: `meta/reports/LAST.md`
- Queue source: `meta/backlog/execution_queue.json`
- Bridge path (single execution bridge):
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_api.py`
- Frontend control plane modules:
  - `frontend/conversation_mode_router.py`
  - `frontend/project_manager_mode.py`
  - `frontend/response_composer.py`
  - `frontend/message_sanitizer.py`
- Verify evidence:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-225449/summary.json`

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Verify summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-000435/summary.json`
- Selftest run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/selftest-1772985437`

