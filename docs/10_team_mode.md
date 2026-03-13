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
- 旧入口 `tools/telegram_cs_bot.py` 已移除，不再作为 support lane 的可运行路径。
- 当前 Telegram/customer-facing 入口统一到 `scripts/ctcp_support_bot.py`。
- 该入口保留 support session artifacts 与 customer-facing reply 壳；项目型消息若要进入 CTCP 执行流，只能经 `scripts/ctcp_front_bridge.py` 创建/绑定/推进 run，不允许在 support bot 内直接改写 project run state。
- 用户可见输出只取 `support_reply.json.reply_text`；provider 调试细节只写 `logs/support_bot.*.log` 与 `TRACE.md`。

## CTCP Support Bot（CEO 口径，双通道）
- 新入口：`scripts/ctcp_support_bot.py`
- 目标：让机械层只决定边界，让 agent 决定表述；用户通道只看自然客服回复，运维通道把 provider 执行细节落到 run_dir 日志。
- 会话 run_dir：
  - `${CTCP_RUNS_ROOT}/<repo_slug>/support_sessions/<chat_id>/`
  - 每条消息都会写入：
    - `artifacts/support_inbox.jsonl`
    - `events.jsonl`（`role=support_bot`）
    - `artifacts/support_session_state.json`
    - `artifacts/support_reply.json`
  - provider 调试日志统一写入 `logs/support_bot.*.log`，并追加 `TRACE.md`。
- 项目型消息接线：
  - support bot 先做 conversation-mode classification。
  - `PROJECT_INTAKE / PROJECT_DETAIL / STATUS_QUERY` 等项目型 turn 只能通过 `scripts/ctcp_front_bridge.py` 创建/绑定/查询/推进 CTCP run。
  - 绑定 run 后，support bot 通过 bridge 读取真实 `RUN.json` / `verify_report.json` 摘要与 `artifacts/support_whiteboard.json` 快照，不直接在客服层发明工程状态。
- 双通道约束：
  - 用户可见只输出 `support_reply.json.reply_text`。
  - 机械层只约束 `reply_text` 的边界：禁止内部泄漏、最多一个关键问题、必须推动一个具体下一步，不强制固定段落结构或标签句式。
  - 禁止在用户回复中出现 `TRACE/logs/outbox/diff --git` 等内部信息。
  - `GREETING / SMALLTALK / PROJECT_* / STATUS_QUERY` 的正常用户可见回复都经 `support_lead` model 生成；mode 只限制后续逻辑边界，不再决定“本地模板 vs 模型回复”。
  - fallback / capability 兜底也必须保持自然客服口吻，不得退回“项目经理方式推进”“API 和本地模型都不可用”这类机械系统句。
  - Telegram 当前对话支持直接发送文件时，客服不得再问邮箱；只有当绑定 run 里存在真实 package/screenshot artifact 时，runtime 才允许直发 `zip/photo`。
  - 若绑定项目目录只是 `main.py + README.md` 这类薄壳占位实现，support package runtime 必须先在 support session 外部 materialize 一份 CTCP-style scaffold，再打包发送；客服回复也必须按 scaffold 如实描述，不得把它说成完整功能已经做完的项目。
- 安全建议：
  - 强烈建议 Telegram 模式配置 `--allowlist`。
  - 不要把 token 写入仓库文件或日志。
  - 所有回写仅允许 `run_dir` 内相对目标路径，禁止绝对路径和 `..` 逃逸。
- provider 路由：
  - 读取 `${run_dir}/artifacts/dispatch_config.json`。
  - 建议样例：`docs/dispatch_config.support_bot.sample.json`
    - `support_lead -> api_agent`
    - `support_local_fallback -> ollama_agent`
    - `patchmaker/fixer -> codex_agent`（可 dry-run）
    - customer-visible support reply 不再 fallback 到 `manual_outbox`；`api_agent` 失败时只降级到本地 provider，并直接告诉用户当前 API reply path 不可用。
    - 正常 greeting/smalltalk 不应绕开 `support_lead` provider，也不应再落到预设机械兜底。
    - 用户要求“发项目包 / 发截图”时，只能发送绑定 run 的真实交付物；如果 `generated_projects/<slug>/` 或 run artifact 中没有对应文件，不允许口头承诺“稍后发送”。
- 使用方式：
```powershell
# stdin 模式（本地适配层）
echo "用户消息" | python scripts\ctcp_support_bot.py --stdin --chat-id local_demo

# Telegram long-poll（stdlib urllib）
python scripts\ctcp_support_bot.py telegram --token "<token>" --poll-seconds 2

# 离线自测（不联网）
python scripts\ctcp_support_bot.py --selftest
```
