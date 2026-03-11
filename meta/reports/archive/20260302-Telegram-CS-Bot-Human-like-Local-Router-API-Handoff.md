# Update 2026-03-02 (Telegram CS Bot Human-like + Local Router -> API Handoff)

### Readlist
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
- `docs/00_CORE.md`
- `docs/10_team_mode.md`
- `agents/prompts/support_lead_reply.md`
- `tools/telegram_cs_bot.py`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

### Plan
1) Docs/Spec 先行：更新任务单、router/reply prompts、dispatch sample 与 team mode 文档。
2) Code：在 `telegram_cs_bot.py` 增加 session state、style 变体、router->handoff 与降级链路。
3) Tests：新增最小覆盖（sanitize、非列表分段、router/handoff 落盘）。
4) Verify：先跑目标单测，再跑 `scripts/verify_repo.ps1` 并记录首个失败点与最小修复。
5) Report：回填 `meta/reports/LAST.md` 后复检。

### Changes
- `agents/prompts/support_lead_router.md`（新增）
  - 新增 router JSON 契约：`route/reason/need_user_confirm/handoff_brief/risk_flags/confidence`。
- `agents/prompts/support_lead_reply.md`
  - 保持 JSON 输出契约，增加“2-4 段、禁列表、每轮主动推进、最多一个关键问题”约束。
- `docs/dispatch_config.support_bot.sample.json`
  - 增加 `support_lead_router/support_lead_reply/support_lead_handoff` 的 provider 映射样例。
- `docs/10_team_mode.md`
  - 补充本地 router + API handoff 行为、失败降级、`support_session_state.json` 说明。
- `tools/telegram_cs_bot.py`
  - 新增会话状态链路：
    - `load_support_session_state(run_dir)`
    - `save_support_session_state(run_dir, state)`
    - run_dir 文件：`artifacts/support_session_state.json`
  - 新增稳定措辞变体：
    - `choose_style(chat_id, turn_index)` + style bank（opener/transition/closer）
    - 每轮回复注入 style hint 并写入 ops 状态
  - 新增 router->handoff 链路：
    - 本地 router prompt 生成 + provider 执行 + 规则回退
    - `artifacts/support_router_trace.jsonl` / `artifacts/support_router.latest.json`
    - `api_handoff` 时写 `artifacts/support_handoff_trace.jsonl`
  - 新增客服回复 provider 链路与优雅降级：
    - local reply 与 api handoff 分 role/provider 执行
    - provider 失败时用户侧仍给自然回复并仅保留 1 个关键问题
    - 失败原因仅写 ops/logs
  - 强化输出约束：
    - `sanitize_customer_reply_text()` 保持内部痕迹清理并保留段落
    - 检测连续列表前缀并 `rewrite_to_paragraphs()`
    - 回复固定为分段式，且每轮包含“下一步推进/默认假设推进”
- `tests/test_support_bot_humanization.py`（新增）
  - Case 1: sanitize 过滤内部痕迹
  - Case 2: 回复分段 + 非列表
  - Case 3: router->handoff 结构化落盘 + handoff brief 透传
- `tests/test_telegram_cs_bot_employee_style.py`
  - 调整断言以匹配新的人性化变体（同问题语义，不强绑固定句式）。
- `meta/tasks/CURRENT.md`
  - 新增本次任务卡 update 与 DoD 映射。

### Verify
- `python scripts/workflow_checks.py` => exit `0`
- `python -m py_compile tools/telegram_cs_bot.py` => exit `0`
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（11 passed）
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（3 passed）
- `python -m py_compile tools/telegram_cs_bot.py tests/test_telegram_cs_bot_employee_style.py tests/test_support_bot_humanization.py` => exit `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - first failure: `workflow gate (workflow checks)`
  - reason: code changes detected but `meta/reports/LAST.md` not updated
  - minimal fix: update `meta/reports/LAST.md` in same patch（本节）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（修复后复检）=> exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=9`)
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-155030` (`passed=14 failed=0`)
  - python unit tests: `Ran 87 tests, OK (skipped=3)`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（最终复检）=> exit `0`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-155618` (`passed=14 failed=0`)

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Router trace: `artifacts/support_router_trace.jsonl` (run_dir)
- Handoff trace: `artifacts/support_handoff_trace.jsonl` (run_dir)

