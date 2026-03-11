# Update 2026-03-02 (CTCP Support Bot CEO口径 + 双通道输出)

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `scripts/ctcp_dispatch.py`
- `tools/providers/manual_outbox.py`
- `tools/providers/ollama_agent.py`
- `tools/providers/codex_agent.py`
- `tools/providers/api_agent.py`
- `tools/telegram_cs_bot.py`
- `docs/10_team_mode.md`
- `meta/tasks/CURRENT.md`

### Plan
1) Docs/Spec first: 任务单与文档先落地本次 Support Bot 约束。
2) Code: 新增 `scripts/ctcp_support_bot.py` + prompt + sample config，并接入 provider 路由与 fallback。
3) Verify: 先做 `py_compile` + `--selftest`，再跑唯一 gate `scripts/verify_repo.ps1`。
4) Report: 回填 `meta/reports/LAST.md`（本节）。

### Changes
- 新增 `scripts/ctcp_support_bot.py`
  - 支持 `--stdin` 与 `telegram --token`。
  - 会话 run_dir 固定在 `${CTCP_RUNS_ROOT}/<repo_slug>/support_sessions/<chat_id>/`（仓库外）。
  - 每条消息写入：
    - `artifacts/support_inbox.jsonl`
    - `events.jsonl`（`role=support_bot`）
    - `artifacts/support_reply.json`
  - provider 路由读取 `${run_dir}/artifacts/dispatch_config.json`，并支持 `manual_outbox/ollama_agent/api_agent/codex_agent/mock_agent`。
  - provider 失败时 fallback `manual_outbox`，并生成安全客服回复。
  - 用户通道只输出 `reply_text`；调试信息落盘 `logs/support_bot.*.log` + `TRACE.md`。
  - 新增 `--selftest`（离线）验证产物路径与回复脱敏规则。
- 新增 `agents/prompts/support_lead_reply.md`
  - 强制 JSON 对象输出（`reply_text/next_question/actions/debug_notes`）。
  - 强制“结论 -> 方案 -> 下一步（一个问题）”口径。
  - 禁止日志/路径/栈信息进入 `reply_text`。
- 新增 `docs/dispatch_config.support_bot.sample.json`
  - 建议默认：
    - `support_lead -> ollama_agent`
    - `patchmaker/fixer -> codex_agent`（可 dry-run）
    - `mode: manual_outbox` 作为 fallback 基线。
- 更新 `tools/providers/manual_outbox.py`
  - 增加 `(\"support_lead\", \"reply\") -> support_lead_reply.md` 模板映射。
- 更新 `docs/10_team_mode.md`
  - 新增 “CTCP Support Bot（CEO 口径，双通道）”使用说明与命令示例。
- 更新 `meta/tasks/CURRENT.md`
  - 新增本次任务 Context / DoD / Acceptance。

### Verify
- `python -m py_compile scripts/ctcp_support_bot.py tools/providers/manual_outbox.py` => exit `0`
- `python scripts/ctcp_support_bot.py --selftest` => exit `0`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/selftest-1772417242`
  - 断言：`artifacts/support_reply.json` 存在，`reply_text` 不含 `TRACE/logs/outbox/diff --git`
- `"请帮我总结下本周项目进展" | python scripts/ctcp_support_bot.py --stdin --chat-id local-smoke --provider manual_outbox` => exit `0`
  - 输出仅为用户可见三段式回复（未夹杂日志）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - `workflow gate`: ok
  - `plan check`: ok
  - `patch check`: ok (`changed_files=10`)
  - `behavior catalog check`: ok
  - `contract checks`: ok
  - `doc index check`: ok
  - `lite scenario replay`: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-100735` (`passed=14 failed=0`)
  - `python unit tests`: `Ran 81 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Selftest run evidence:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/selftest-1772417242/artifacts/support_reply.json`
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/support_sessions/selftest-1772417242/logs/support_bot.provider.log`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-100735/summary.json`

