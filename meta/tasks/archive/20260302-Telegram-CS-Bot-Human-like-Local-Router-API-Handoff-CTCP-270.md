# Update 2026-03-02 - Telegram CS Bot Human-like + Local Router -> API Handoff (CTCP 2.7.0)

### Context
- 用户要求把 `tools/telegram_cs_bot.py` 从“单一路由+模板式回复”升级为“更像真人客服”的对话链路：
  - 每轮主动推进，不等“继续”
  - 分段自然表达（2-4 段），避免条目列表腔
  - 会话状态连续记忆（summary/confirmed/open questions）
  - 本地 router 先决策，必要时 handoff 到 API agent
  - 保持用户通道干净，ops 通道留痕

### DoD Mapping (from request)
- [x] DoD-1: 新增 `support_session_state.json` 状态链路并每轮读写。
- [x] DoD-2: 新增 `support_lead_router` prompt 与 router->handoff 代码路径（含失败优雅降级）。
- [x] DoD-3: 回复满足“非列表、分段、措辞稳定变化、每轮推进”并保持 sanitize 不退化。
- [x] DoD-4: 更新 `docs/dispatch_config.support_bot.sample.json` 与 `docs/10_team_mode.md` 说明。
- [x] DoD-5: 新增最小单测覆盖 sanitize / 分段非列表 / router-handoff 落盘。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

