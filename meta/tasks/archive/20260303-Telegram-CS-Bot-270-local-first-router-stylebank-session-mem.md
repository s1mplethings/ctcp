# Update 2026-03-03 - Telegram CS Bot 2.7.0：local-first router + stylebank + session memory 对齐

### Context
- 用户要求把客服 bot 升级为“更像真人 + 主动推进 + 本地路由后按需升级 API”，并保持 CTCP 核心契约不变（run_dir 外置、双通道日志、可验证闭环）。
- 当前实现已具备基础 router/handoff/memory，但路由 schema、StyleBank 选择因子与测试入口还未完全对齐目标交付。

### DoD Mapping (from request)
- [x] DoD-1: `agents/prompts/support_lead_router.md` 升级为严格 JSON 路由契约（`route/intent/confidence/followup_question/style_seed/risk_flags`，local-first，最多一个问题）。
- [x] DoD-2: `agents/prompts/support_lead_reply.md` 升级为 2-4 段自然表达 + `style_seed` 入口 + 禁止列表风格，同时保持单 JSON 输出。
- [x] DoD-3: `tools/telegram_cs_bot.py` 接入新路由枚举（`local/api/need_more_info/handoff_human`）与优雅降级；新增会话状态字段 `last_intent/last_style_seed` 并持续更新。
- [x] DoD-4: 新增 `tools/stylebank.py`，实现 `sha256(chat_id|intent|turn_index|style_seed)` 的确定性措辞变体选择，并接入 bot。
- [x] DoD-5: 新增 `tests/test_support_router_and_stylebank.py`，覆盖 StyleBank 确定性、路由升级逻辑与用户输出断言。
- [x] DoD-6: 文档补充路由/升级/查看进度说明，不暴露内部绝对路径。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

