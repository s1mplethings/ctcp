# Team Mode (Autonomous Coding Team)

Scope boundary:
- This is a team-mode lane document, not the repository purpose definition.
- Repo purpose source: `docs/01_north_star.md`.
- Canonical repository execution flow source: `docs/04_execution_flow.md`.

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
  - 每条用户消息先走本地 router（建议 `support_lead_router -> ollama_agent`），输出严格 JSON：`route/intent/confidence/followup_question/style_seed/risk_flags`。
  - router 路由枚举：`local`（默认）、`api`（复杂任务升级）、`need_more_info`（仅一个关键问题）、`handoff_human`（人工升级）。
  - 当 route 为 `api` 或 `handoff_human` 时，bot 会把 `handoff_brief` 交给 API agent（建议 `support_lead_handoff -> api_agent/codex_agent`）生成最终客服回复。
  - 当本地模型或 API provider 任一失败时，bot 自动优雅降级：用户侧仍给自然回复（最多 1 个关键问题 + 默认推进假设），失败细节仅写 run_dir 运维日志。
  - 会话状态会落盘到 `artifacts/support_session_state.json`（`user_goal/confirmed/open_questions/last_action_taken/session_summary/turn_index/last_intent/last_style_seed`）。
  - 会话记忆采用 slot-like 结构：在 `support_session_state.json` 里维护 `memory_slots`（`customer_name/preferred_style/current_topic/last_request`）用于跨轮延续语境。
  - 目标对齐采用 `execution_focus`：每轮维护 `execution_goal + execution_next_action`，确保 bot 始终知道“当前要做什么”并在回复中体现推进动作。
  - StyleBank 使用确定性算法：`sha256(chat_id|intent|turn_index|style_seed)`，保证同输入可回放、跨轮次可变化。
  - 清理/删除项目策略：默认先 `archive + unbind`，若用户要求永久删除，必须显式确认后再执行。
  - 纯寒暄（如“你好/谢谢/你能做什么”）优先走本地小回复路径，不触发工程路由问题，避免“想到什么说什么”。
  - 关键追问去重：同一追问在未获得新信息前不重复发送，默认改为“我先继续推进”的执行口径。
  - 任务导向硬约束：
    - 禁止“接着聊/我在呢/先聊聊看”式空泛续聊开场；
    - 首句必须完成任务定向（问题排查/需求咨询/项目继续/方案比较/资料收集）；
    - 每轮至少推进一个具体动作（请求明确输入或给出有限选项）；
    - 仅在用户显式表示“继续上次项目”时引用历史项目上下文。
  - 每次对话可产出 `artifacts/API_BOT_SUMMARY.md`，并生成 `inbox/apibot/requests/REQ_*.json`。
  - 派发 `Type: agent_request` 时会自动附带 `USER_NOTES` 与 `API_BOT_SUMMARY` 尾部，帮助其他 agent 快速执行。
  - 设计目标：让机械层只决定边界，让 agent 决定表述。
  - 员工感增强：默认输出 2-4 段自然对话，避免条目列表；每轮都包含“我现在就推进的下一步”。
  - 进度口径增强：`status/advance/TRACE` 主动推送会整理成客户可直接理解的自然进展，不强制固定标题或固定三段句式。
  - 对话降噪：自然聊天写入 `USER_NOTES` 时默认不再回显文件路径；如需保留路径回显可设置 `CTCP_TG_NOTE_ACK_PATH=1`。
  - 双通道契约：机械层只负责内部词泄漏防护、最多一个关键问题、每轮至少推进一个具体动作；具体措辞由 agent 自然生成，内部事件/key/path 仅写入 run_dir 日志。
  - 所有用户可见通知（包括 report / bundle / agent dispatch / agent result / write-fail）都必须走同一自然客服出口，不得直出 `verify_report.json`、`failure_bundle.zip`、`internal agent`、raw exception 等内部词。
  - 显式进度开关：用户发送“查看进度”或 `debug`（或 `/debug`）时才推送里程碑摘要；默认只输出可客户理解的里程碑摘要，不回显内部 key/path/trace。
  - blocked 去重与冷却：同一阻塞原因短时间内只提醒一次；默认不再循环追问“是否继续自动推进”。
  - 用户补充信息后会自动清除 blocked 冷却并继续推进，不需要额外发“继续”。
  - 无 active run 的纯寒暄/致谢/能力询问保持本地客服回复，不为这类消息自动创建 run。
  - 当用户问“你能做什么/能不能改前端”这类能力问题时，本地回复可以明确说明能处理前端表现、桥接边界内的执行接入、回归测试与任务推进，但不能绕过 bridge 直接改运行态。
  - Telegram 新建 run 时会先校准工程 dispatch provider：若外部 API 环境未真正就绪，则自动降级为 `manual_outbox`，避免 `OPENAI_API_KEY=ollama` 但无 `OPENAI_BASE_URL` 这类误配置直接打出 401。
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
- 目标：让机械层只决定边界，让 agent 决定表述；用户通道只看自然客服回复，运维通道把 provider 执行细节落到 run_dir 日志。
- 会话 run_dir：
  - `${CTCP_RUNS_ROOT}/<repo_slug>/support_sessions/<chat_id>/`
  - 每条消息都会写入：
    - `artifacts/support_inbox.jsonl`
    - `events.jsonl`（`role=support_bot`）
    - `artifacts/support_reply.json`
  - provider 调试日志统一写入 `logs/support_bot.*.log`，并追加 `TRACE.md`。
- 双通道约束：
  - 用户可见只输出 `support_reply.json.reply_text`。
  - 机械层只约束 `reply_text` 的边界：禁止内部泄漏、最多一个关键问题、必须推动一个具体下一步，不强制固定段落结构或标签句式。
  - 禁止在用户回复中出现 `TRACE/logs/outbox/diff --git` 等内部信息。
  - fallback / smalltalk / capability 兜底也必须保持自然客服口吻，不得退回“项目经理方式推进”“API 和本地模型都不可用”这类机械系统句。
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
