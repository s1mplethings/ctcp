# Update 2026-02-27 (Telegram CS API router + APIBOT summary)

### Goal
- 把 Telegram bot 从“关键词记录器”升级为“API 客服 + agent 工作总结器”，保持 CTCP 核心默认离线流程不变。

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `docs/30_artifact_contracts.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `scripts/workflow_checks.py`
- `scripts/ctcp_orchestrate.py`

### Plan
1) Docs/Spec：更新任务单与 team mode 文档，先定义客服 API 与 summary 约束。
2) Code：新增 `tools/telegram_cs_bot.py`，实现 Telegram long-poll、run_dir 主动推送、回写、agent bridge、API 路由。
3) Verify：运行 `python -m py_compile tools/telegram_cs_bot.py` 与 `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`。
4) Report：回填本节 Verify、Changes、Demo。

### Changes
- `tools/telegram_cs_bot.py`
  - 新增可运行 bot（stdlib 实现 Telegram Bot API long-poll）。
  - 支持：新建 run、自然语言补充需求、`/status` `/advance` `/outbox` `/get` `/bundle` `/lang` `/note`。
  - 支持：question inline buttons、回复消息文本/文件写回 `Target-Path`、run_dir 路径安全校验。
  - 支持：`Type: agent_request` 文件投递到 `inbox/<agent>/requests`，消费 `results` 回写目标。
  - 新增：API 客服路由（OpenAI 兼容）与 `API_BOT_SUMMARY` 生成，并注入 agent_request payload。
  - 新增：无 API 时的日常寒暄兜底回复（如“你好/谢谢/你能做什么”），避免统一回落为 `USER_NOTES` 记录提示。
- `docs/10_team_mode.md`
  - 新增“对话式 Telegram 客服（可选）”章节，说明自然语言主用法、API 配置、summary 产物、安全建议。
- `meta/tasks/CURRENT.md`
  - 新增本次任务更新节与验收项。
- `meta/reports/LAST.md`
  - 追加本次 Readlist/Plan/Changes/Verify/Demo 记录。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py` => PASS（exit 0）
- `python -c "import tools.telegram_cs_bot as b; print('ok')"` => PASS（exit 0, import 无网络副作用）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => PASS（exit 0）
  - `workflow_checks`: ok
  - `patch_check`: ok (`changed_files=4`)
  - `lite scenario replay`: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-180416/summary.json` (`passed=14 failed=0`)
  - `python unit tests`: `Ran 73 tests, OK (skipped=3)`
  - recheck after `git add -N tools/telegram_cs_bot.py`: PASS（workflow gate 识别到代码改动后仍通过）

### Demo
- 运行（PowerShell）：
  - `python tools\\telegram_cs_bot.py`
- 对话路径：
  - 首句目标自动新建 run。
  - 后续自然语言需求写入 `artifacts/USER_NOTES.md`。
  - API 总结输出：`artifacts/API_BOT_SUMMARY.md` 与 `inbox/apibot/requests/REQ_*.json`。
  - agent bridge 路径：`inbox/<agent>/requests` 与 `inbox/<agent>/results`。

### Update 2026-02-27 (status/advance natural-language replies)
- 用户反馈 `advance` 与 `status` 回答过于原始日志化，影响聊天体验。
- `tools/telegram_cs_bot.py` 已改为自然语言总结：
  - `advance`：优先输出“已推进/被阻塞 + 原因 + owner + target-path + 状态/迭代”
  - `status`：输出“运行目录 + pending 计数 + 最新 TRACE 事件”
- 同时保留原有 run_dir 投递与契约行为，不改核心流程。
- Verify:
  - `python -m py_compile tools/telegram_cs_bot.py` => PASS（exit 0）
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => PASS（exit 0）
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-215736/summary.json`（passed=14 failed=0）

### Update 2026-02-27 (unstick: OpenAI payload surrogate-safe)
- 现象：run 在 `waiting for file_request.json` 阶段反复失败，日志显示 `agent command failed rc=1`。
- 根因：`scripts/externals/openai_responses_client.py` 在构造 JSON payload 时遇到非法 surrogate 字符，触发 `UnicodeEncodeError`。
- 修复：
  - 新增 `_sanitize_text_for_json()`，在发请求前将 prompt 做 UTF-8 安全清洗。
  - `responses` 与 `chat` 两条 API 路径统一改用 `safe_prompt`。
- 验证：
  - `python -m py_compile scripts/externals/openai_responses_client.py tools/telegram_cs_bot.py` => PASS（exit 0）
  - surrogate 冒烟：`_sanitize_text_for_json('ok\\udca8x')` 输出无 surrogate。
  - run 恢复推进：`file_request.json` 与 `context_pack.json` 均已生成，当前进入 `waiting for PLAN_draft.md`。
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => PASS（exit 0）
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-224827/summary.json`（passed=14 failed=0）

### Update 2026-03-01 (dialogue/progress full-flow test)
- 目标：验证“对话问答 + 进度说明 + 连续推进”全链路，不因误判而卡住。
- 对话联测（bot harness, api_enabled=0, 强制规则兜底）：
  - 输入“有什么需要我决定的吗”可直接返回“有/无待决事项”，不再反问用户。
  - 输入“进度”返回自然语言状态摘要（run_dir、pending 计数、最新 TRACE 事件）。
  - 输入“继续”返回自然语言推进摘要（含阻塞原因、owner、target-path）。
- 当前工作仓库联测结果：
  - 连续推进至 `ready_apply` 后触发 `repo_dirty_before_apply`（由于仓库有未提交改动，属于安全门禁预期行为）。
- 干净 worktree 全流程联测（`CTCP_FORCE_PROVIDER=mock_agent`）：
  - run: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp_clean_flow_test_wt/20260301-034137-013895-orchestrate`
  - 12 步完成全流程：`analysis -> find -> file_request -> context_pack -> PLAN_draft -> reviews -> PLAN -> diff.patch -> apply -> verify -> pass`
  - 最终状态：`run_status=pass`，无“卡死”。
- 门禁回归：
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => PASS（exit 0）
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260301-033658/summary.json`（passed=14 failed=0）

