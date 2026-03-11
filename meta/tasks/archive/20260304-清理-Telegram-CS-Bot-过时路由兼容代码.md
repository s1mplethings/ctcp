# Update 2026-03-04 - 清理 Telegram CS Bot 过时路由兼容代码

### Context
- 用户要求“按照文档检查并清理不要的代码”，并确认“直接全部清理”。
- 文档约束已明确 router 契约使用 `route/intent/confidence/followup_question/style_seed/risk_flags`，本地代码仍保留旧兼容字段和旧路由别名处理。

### DoD Mapping (from request)
- [x] DoD-1: 清理 `tools/telegram_cs_bot.py` 中过时路由兼容输出字段（`route_legacy`）与旧字段回退逻辑（`need_user_confirm`）。
- [x] DoD-2: 清理旧路由别名兼容分支（`api_handoff` / `local_reply`），统一使用文档契约路由值。
- [x] DoD-3: 同步更新相关测试输入与断言，避免继续依赖过时字段/路由名。
- [x] DoD-4: 通过 `scripts/verify_repo.ps1` 全门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

