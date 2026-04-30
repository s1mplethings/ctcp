# Team Mode Runtime Wiring

Scope boundary:
- This file is the runtime-wiring and support-orchestration contract for team-mode behavior.
- It is not the authoritative definition of Virtual Team Lane design behavior.
- Repo purpose source: `docs/01_north_star.md`.
- Canonical repository execution flow source: `docs/04_execution_flow.md`.
- Virtual Team Lane authority source: `docs/12_virtual_team_contract.md`.

目标：让 runtime / support / frontdesk 能把 CTCP 的正式工作车道接到用户可见层，而不是在这里重新定义产品设计流程。
任务推进型对话权威合同：`docs/11_task_progress_dialogue.md`。
人格测试与风格回归权威合同：`docs/14_persona_test_lab.md`。

## 车道职责边界

- `Delivery Lane`
  - 用于边界明确、局部实现、直接交付类任务
  - 本文只负责 support/frontdesk 如何接线、展示、回放和桥接真实状态
- `Virtual Team Lane`
  - 用于新项目、模糊目标、需要系统自行做产品/架构/UX 决策的任务
  - 正式设计行为、角色职责、必须产物、进入实现的闸门都由 `docs/12_virtual_team_contract.md` 定义

硬规则：
- 本文不得再充当“虚拟项目团队设计合同”的唯一来源
- support/runtime 可以路由到 Virtual Team Lane，但不得在没有设计产物时伪造“团队已经设计完成”
- 若本文与 `docs/12_virtual_team_contract.md` 冲突，以后者为准

## 核心目录
- `meta/tasks/CURRENT.md`：任务单（验收/计划/是否允许改代码）
- `${CTCP_RUNS_ROOT:-~/.ctcp/runs}/ctcp/<run_id>/`：一次“团队运行包”（真实路径）
  - `PROMPT.md`：给 coding agent 的 compiled prompt 输入；它由 `AGENTS.md` + routed lane contract + `meta/tasks/CURRENT.md` 派生，不是独立权威
  - `QUESTIONS.md`：run 级阻塞问题产物；不得反向覆盖 root/task/routed contracts
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
- 该入口保留 support session artifacts 与 customer-facing reply 壳；项目型消息若要进入 CTCP 执行流，只能经 `scripts/ctcp_front_bridge.py` 的单入口 `ctcp_sync_support_project_turn` 做创建/绑定/记录/推进，不允许在 support bot 内直接改写 project run state。
- 用户可见输出只取 `support_reply.json.reply_text`；provider 调试细节只写 `logs/support_bot.*.log` 与 `TRACE.md`。

## CTCP Support Bot（CEO 口径，双通道）
- 新入口：`scripts/ctcp_support_bot.py`
- 目标：让机械层决定任务推进边界与展示链，让 agent 在这些边界内输出任务推进型回复；用户通道只看 grounded reply，运维通道把 provider 执行细节落到 run_dir 日志。
- 风格合同：
  - `docs/11_task_progress_dialogue.md` 是任务推进型回复与 response lint 的单一权威来源。
  - 客服/前台/support 的“硬约束”也统一收敛到 `docs/11_task_progress_dialogue.md`，包含：反机械寒暄、反重复无增量、状态切换必回应、无状态变化默认少说、完成声明必须绑定 run truth、最终交付闭环字段。
  - `docs/14_persona_test_lab.md` 是隔离式人格测试、评分和回归 case 的单一权威来源。
  - 本文以及历史报告中关于“自然客服口吻 / CEO 口径 / 不要机械”之类的软描述继续保留为设计意图；若与 `docs/11_task_progress_dialogue.md` 冲突，视为 superseded。
- 会话 run_dir：
  - `${CTCP_RUNS_ROOT}/<repo_slug>/support_sessions/<chat_id>/`
  - 每条消息都会写入：
    - `artifacts/support_inbox.jsonl`
    - `events.jsonl`（`role=support_bot`）
    - `artifacts/support_session_state.json`
    - `artifacts/support_reply.json`
  - provider 调试日志统一写入 `logs/support_bot.*.log`，并追加 `TRACE.md`。
- 项目型消息接线：
  - 单主流程硬规则：support runtime 禁止触发 `run_t2p_state_machine()` 的快速脚手架旁路（含 `telegram_ingress_sanity` / `fallback_generation`）；项目型 turn 只能进入 bridge 主流程状态机，并统一经 `ctcp_sync_support_project_turn`。
  - support bot 先做规则型 conversation-mode 首判；若命中歧义/解释型 turn（例如已绑定 run 下的“为什么会这样”），runtime 可触发 model-assisted 二段仲裁（api-first，失败降级到本地），再决定最终 mode。
  - 在任何 prompt/reply 生成前，runtime 还必须基于 latest turn、active run、session slots 解析一层显式 frontdesk state machine；权威结构见 `docs/architecture/contracts/frontend_session_contract.md`。
  - 这层 frontdesk state machine 至少要覆盖 `Idle / IntentDetect / Collect / Clarify / Confirm / Execute / AwaitDecision / ReturnResult / InterruptRecover / StyleAdjust / Error`，并持久化 `current_goal / current_scope / active_task_id / waiting_for / user_style_profile / decision_points / artifacts / blocked_reason / resumable_state`。
  - support session state 必须额外持久化单主任务真值：`active_task_id / active_run_id / active_goal / active_stage / active_blocker / active_next_action`；除 `new_task` 之外的 turn 不得无标记覆盖该主线。
  - 会话历史必须分层为 `raw_turns / working_memory / task_summary / user_preferences`；前台 prompt 默认消费 `working_memory + task_summary + 最近少量 raw_turns`，禁止把全量 raw 对话直接当唯一上下文。
  - 每条新消息必须先写入 `message_intent` 分类（`continue|clarify|constraint_update|new_task|small_talk|status_check`），再决定是否继续当前主线或显式切换任务。
  - 处理顺序必须是：先判断 frontdesk state，再决定回复策略，再生成回复内容；`visible_state` 只是用户可见执行态折叠，不能替代 frontdesk state。
  - `PROJECT_INTAKE / PROJECT_DETAIL / STATUS_QUERY` 等项目型 turn 只能通过 `scripts/ctcp_front_bridge.py::ctcp_sync_support_project_turn` 执行创建/绑定/记录/推进，再通过 `get_support_context`/snapshot 接口读取真值。
  - 首轮创建 run 的质量提升约束（如 `build_profile=high_quality_extended`、首轮质量标记）也必须仅通过该单入口 payload 传入 `frontend_request`，禁止 support 侧旁路写入。
  - 当 bound run 的 `status.gate.state=blocked` 时，runtime 只允许输出 grounded 状态与下一步，不允许注入“已完成生成/已可交付包”的快通道语义。
  - 绑定 run 后，support bot 只能消费 bridge/back-end 提供的 `get_support_context` / `get_current_state_snapshot` / `get_render_state_snapshot` / artifact interfaces；兼容性文件读取只允许留在 bridge/backend 内部，不得在客服层直接扫描 `RUN.json` / `verify_report.json` / `TRACE.md` 伪造工程真值。
  - 在发出 `support_reply.json.reply_text` 前，reply builder 必须绑定 `task_goal / current_phase / last_confirmed_items / current_blocker / message_purpose / question_needed / next_action`。
  - `style_change` 必须只更新持久 `user_style_profile`，不得覆盖当前任务主线；`clarify / redirect / override / sidequest / status_query / result_query` 等中断分类必须显式写入 frontdesk state，并保留 `resumable_state`。
  - 对 `STATUS_QUERY` 以及“继续按这个做 / 现在做到什么程度了”这类 status-like progress follow-up，runtime 必须消费 bound run 的 gate/status 与 whiteboard tail，自动总结已完成事项、当前阶段、当前阻塞或 clear path、以及下一步；不得退回 `EXECUTING` 固定壳文案。
  - 对“之前那个项目现在做成什么样了 / 之前的项目现在怎么样”这类旧项目状态追问，runtime 必须优先走 `STATUS_QUERY`/grounded progress path（即使当前未绑定 run 也不得回退成新的 intake 创建）；不得把这类句子写回长期 `project_brief`，也不得因此触发新的 planning/file-request 轮次。
  - Telegram long-poll 在空闲轮询周期里必须检查 active bound run：若 run 仍可推进且不需要用户决策，runtime 可自动 `advance`；一旦 grounded progress digest 发生变化，必须主动发送一条新的 progress update，而不是等用户追问。
  - 后台主动通知判定必须由独立 support controller 负责（规则优先，基于 bridge/run truth），support bot 只负责 Telegram 收发与 outbound job 发送，不得再把“该不该通知/该发哪类通知”分散在文案层分支里。
  - 若用户显式要求“按之前的大纲 / 之前的项目继续”，而当前会话只有 generic previous-project 占位语，runtime 必须优先恢复 archived support session 里的 concrete project brief，再创建或重绑 run；不得把这类句子直接当成一个新的空泛 goal。
- 双通道约束：
  - 用户可见只输出 `support_reply.json.reply_text`。
  - 机械层只约束 `reply_text` 的边界：禁止内部泄漏、最多一个关键问题、必须推动一个具体下一步，并且首句直入任务本体。
  - 禁止在用户回复中出现 `TRACE/logs/outbox/diff --git` 等内部信息。
  - `GREETING / CAPABILITY_QUERY / SMALLTALK / PROJECT_* / STATUS_QUERY` 的正常用户可见回复都经 `support_lead` model 生成；mode 只限制后续逻辑边界，不再决定“本地模板 vs 模型回复”。
  - `GREETING / CAPABILITY_QUERY / SMALLTALK` turn 默认不得把旧项目摘要、bound run、package/screenshot delivery 状态继续注入 prompt；只有当最新 user turn 明确要求继续旧项目或直接请求交付时，runtime 才允许带入这些上下文。
  - proactive progress push 复用同一条 grounded status reply path；不得另外生成一套未绑定 run truth 的“自动播报模板”。
  - proactive progress push 不得直接复用 inbox 里的最新 greeting/smalltalk 作为 latest-turn 语义；它必须显式以 status/progress 语义渲染，避免“用户问候一次，系统主动再问候一次”的重复输出。
  - greeting / capability / smalltalk 这类 non-project turn 在 active bound run 上不得重置 `notification_state` 里的真实 progress baseline；若 run digest 本身没有变化，后续 idle cycle 不应把同一状态再主动推一次。
  - fallback / capability 兜底也必须保持任务推进型口吻，不得退回“项目经理方式推进”“API 和本地模型都不可用”这类机械系统句。
  - Telegram 当前对话支持直接发送文件时，客服不得再问邮箱；`send_project_package` 只允许在绑定 run 满足“`verify_result=PASS` 且 `run_status` 已到最终态（`pass/done/completed/success`）且无待用户决策”时触发；另外必须通过 package 质量门禁（至少满足最小质量分和核心展示证据），否则即使有 artifact 也禁止发包。截图交付仍按实际截图 artifact 可用性决定。
  - project-generation 交付默认对外 document 必须是 `final_project_bundle.zip`；`process_bundle.zip` 只作为内部调试/复盘产物记录在 manifest，不得默认作为用户主交付。
  - 若绑定项目目录只是 `main.py + README.md` 这类薄壳占位实现，support package runtime 必须先在 support session 外部 materialize 一份 CTCP-style scaffold，再打包发送；客服回复也必须按 scaffold 如实描述，不得把它说成完整功能已经做完的项目。
  - 若 turn 涉及测试、演示、截图、回放或交付说明，reply 必须优先引用 `artifacts/test_plan.json`、`artifacts/test_cases.json`、`artifacts/test_summary.md`、`artifacts/demo_trace.md`、`artifacts/screenshots/` 等真实展示产物；没有截图时必须如实说明没有。
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

## Persona Test Lab（隔离式风格回归层）

- Persona Test Lab 不是 production conversation path 本身，它只负责验证 production assistant 是否仍然会退回机械客服腔。
- 三层必须分离：
  - `production_assistant`: 正式执行人格，只负责给出任务推进型回复。
  - `test_user_persona`: 固定脚本化测试用户，只负责压测回复风格和任务推进质量。
  - `judge/scoring`: 读取 transcript 和 rubric 给出分数、fail reasons、pass/fail verdict。
- 每个 case 都必须在新会话里运行，不能复用 production support session，也不能读取上一条 persona case 的聊天上下文。
- repo 里只保存静态 persona/rubric/case 资产：
  - `persona_lab/personas/`
  - `persona_lab/rubrics/`
  - `persona_lab/cases/`
- 实际 transcript / score / fail reasons / summary 只能写到 repo 外的 `CTCP_RUNS_ROOT/<repo_slug>/persona_lab/<lab_run_id>/...`。
- judge 层不得回写 `support_session_state.json`、`RUN.json` 或其他 production run artifacts；它只能写 persona-lab 自己的结果产物。
- 若本轮 patch 影响 task-progress dialogue、support style contract、response lint 或 multilingual style acceptance，必须同步更新 `docs/14_persona_test_lab.md` 和相关 `persona_lab/` 资产，或者在任务卡里明确 `persona_lab_impact: none`。

