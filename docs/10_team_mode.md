# Team Mode (Autonomous Coding Team)

目标：让你只输入一次 Goal，系统像项目团队一样持续推进，并给你演示。

## 核心目录
- `meta/tasks/CURRENT.md`：任务单（验收/计划/是否允许改代码）
- `${CTCP_RUNS_ROOT:-~/.ctcp/runs}/ctcp/<run_id>/`：一次“团队运行包”（真实路径）
  - `PROMPT.md`：给 coding agent 的输入（唯一入口）
  - `QUESTIONS.md`：阻塞问题（唯一允许提问渠道）
  - `TRACE.md`：全过程日志（演示）
- `meta/run_pointers/LAST_RUN.txt`：仓库内指针（记录最新 run 包绝对路径）
- `meta/reports/LAST.md`：面向你的演示报告（可回放）

## 使用
1) 创建运行包：
```powershell
python scripts\ctcp_orchestrate.py new-run --goal "your goal"
```

2) 持续推进状态机（直到 PASS 或产生 failure bundle）：
```powershell
python scripts\ctcp_orchestrate.py advance --max-steps 16
```

3) agent 产出 patch/改动后，跑：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1
```

4) 演示：
- 打开 `meta/reports/LAST.md`
- 跟着 Trace 指针回放外部 run 包中的 `TRACE.md`

## codex_agent Provider（可选全自动）
- 用途：当 `dispatch_config` 选择 `codex_agent` 时，dispatcher 会自动调用本机 `codex exec` 生成目标 artifact（例如 `artifacts/diff.patch`、`artifacts/PLAN_draft.md`）。
- 默认安全策略：`codex_agent` 默认禁用/可 dry-run，CI 与 `verify_repo` 默认不会触发真实调用。
- 启用方式：
  - 复制 `docs/dispatch_config.codex_agent.sample.json` 到 `${run_dir}/artifacts/dispatch_config.json`。
  - 按需设置 `providers.codex_agent.enabled=true`，或用环境变量 `CTCP_CODEX_AGENT=1` 覆盖。
- 产物与日志：
  - 目标产物写入 `${run_dir}/<target_path>`（严格 run_dir 范围）。
  - 执行日志写入 `${run_dir}/logs/dispatch_codex_agent.stdout.log` 与 `${run_dir}/logs/dispatch_codex_agent.stderr.log`。

## 对话式 Telegram 客服（可选）
- 用途：把 `run_dir/outbox/TRACE` 变成聊天入口，不改变默认 headless/离线流程。
- 主用法（自然语言）：
  - 用户第一句直接说目标，例如“做一个新程序”，bot 自动 `new-run` 并绑定 `run_dir`。
  - 绑定后继续聊天补充需求，bot 会记录到 `artifacts/USER_NOTES.md`。
  - 全自动推进：没有待决问题时，bot 会持续自动 `advance`，不需要手动发“继续”。
  - 用户问“进度/卡点/继续/发报告”，bot 自动识别并执行 `status/advance/report` 类动作。
  - `status/advance` 回复会优先用自然语言总结（阻塞原因、负责人、目标路径等），避免直接暴露原始日志块。
  - bot 后台主动推送：`Type: question`、普通 outbox、`failure_bundle.zip`、`TRACE` 增量。
- API 客服层（可选）：
  - bot 可通过 OpenAI 兼容 API 做意图路由和客服回复（默认开启，可用 `CTCP_TG_API_ENABLED=0` 关闭）。
  - 每次对话可产出 `artifacts/API_BOT_SUMMARY.md`，并生成 `inbox/apibot/requests/REQ_*.json`。
  - 派发 `Type: agent_request` 时会自动附带 `USER_NOTES` 与 `API_BOT_SUMMARY` 尾部，帮助其他 agent 快速执行。
  - 员工感增强：无论 API/非 API 路径，bot 默认先确认用户诉求、说明下一步动作，并在缺关键信息时最多追问 1~2 个澄清问题（渠道、转人工、知识库来源）。
  - 进度口径增强：`status/advance/TRACE` 主动推送默认使用“现在打算做什么 / 刚做完什么 / 关键问题”三段式，面向客户可直接理解。
  - 对话降噪：自然聊天写入 `USER_NOTES` 时默认不再回显文件路径；如需保留路径回显可设置 `CTCP_TG_NOTE_ACK_PATH=1`。
  - 双通道契约：用户通道只发“结论 -> 方案 -> 下一步”三段式；内部事件/key/path 仅写入 run_dir 日志。
  - 显式进度开关：用户发送“查看进度”或 `debug`（或 `/debug`）时才推送里程碑摘要；默认不主动展示内部推进细节。
  - 运维日志位置：run_dir 下 `logs/telegram_cs_bot.ops.jsonl`（仅内部使用，不回显给用户）。
- 启动示例：
```powershell
$env:CTCP_TG_BOT_TOKEN="<token>"
$env:CTCP_TG_ALLOWLIST="123456789"               # 可选
$env:CTCP_REPO_ROOT="D:\.c_projects\adc\ctcp"    # 可选
$env:CTCP_TG_STATE_DB="$HOME\.ctcp\telegram_bot\state.sqlite3"  # 可选
$env:CTCP_TG_POLL_SECONDS="2"                    # 可选
$env:CTCP_TG_TICK_SECONDS="2"                    # 可选
$env:CTCP_TG_API_ENABLED="1"                     # 可选（默认 1）
$env:CTCP_TG_NOTE_ACK_PATH="0"                   # 可选（默认 0，不回显 USER_NOTES 路径）
$env:CTCP_TG_API_MODEL="gpt-4.1-mini"            # 可选
python tools\telegram_cs_bot.py
```
- 安全建议：
  - 强烈建议配置 `CTCP_TG_ALLOWLIST`。
  - 不要把 token 写入仓库文件或日志。
  - 所有回写仅允许 `run_dir` 内 `Target-Path`，禁止绝对路径和 `..` 逃逸。

## CTCP Support Bot（CEO 口径，双通道）
- 新入口：`scripts/ctcp_support_bot.py`
- 目标：用户通道只发自然客服结论；运维通道把 provider 执行细节落到 run_dir 日志。
- 会话 run_dir：
  - `${CTCP_RUNS_ROOT}/<repo_slug>/support_sessions/<chat_id>/`
  - 每条消息都会写入：
    - `artifacts/support_inbox.jsonl`
    - `events.jsonl`（`role=support_bot`）
    - `artifacts/support_reply.json`
  - provider 调试日志统一写入 `logs/support_bot.*.log`，并追加 `TRACE.md`。
- 双通道约束：
  - 用户可见只输出 `support_reply.json.reply_text`。
  - `reply_text` 强制为“结论 -> 方案 -> 下一步（一个问题）”。
  - 禁止在用户回复中出现 `TRACE/logs/outbox/diff --git` 等内部信息。
- provider 路由：
  - 读取 `${run_dir}/artifacts/dispatch_config.json`。
  - 建议样例：`docs/dispatch_config.support_bot.sample.json`
    - `support_lead -> ollama_agent`
    - `patchmaker/fixer -> codex_agent`（可 dry-run）
    - provider 失败时 fallback 到 `manual_outbox`。
- 使用方式：
```powershell
# stdin 模式（本地适配层）
echo "用户消息" | python scripts\ctcp_support_bot.py --stdin --chat-id local_demo

# Telegram long-poll（stdlib urllib）
python scripts\ctcp_support_bot.py telegram --token "<token>" --poll-seconds 2

# 离线自测（不联网）
python scripts\ctcp_support_bot.py --selftest
```
