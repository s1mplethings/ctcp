# Update 2026-02-27 - Telegram CS API router + APIBOT summary

### Context
- 用户反馈当前 Telegram bot 更像“记录器”，希望升级为“客服型”对话入口：接入 API 做意图理解，并生成可投递给其他 agent 的总结。
- 约束：保持可选工具属性，不改变 CTCP 核心默认离线路径和 verify 入口。

### DoD Mapping (from request)
- [x] DoD-1: 新增 `tools/telegram_cs_bot.py`（stdlib + 本仓库 API 客户端）并支持对话式入口。
- [x] DoD-2: API 客服路由可将自然语言映射为 `status/advance/outbox/bundle/report/lang/note`。
- [x] DoD-3: 生成 `artifacts/API_BOT_SUMMARY.md` 与 `inbox/apibot/requests/REQ_*.json`，并在 agent_request 派发时附带 summary tail。
- [x] DoD-4: 维持 outbox/question/Target-Path 回写、agent bridge requests/results、TRACE/bundle 主动推送。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

