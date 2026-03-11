# Update 2026-03-02 - my_test_bot 真人客服化（寒暄优先 + 会话记忆 + 去工程口吻）

### Context
- 用户反馈当前会话回复仍偏工程流水：例如“我已经推进到下一里程碑”“先按 patch 路径推进吗”，不像真人客服。
- 目标：把 `tools/telegram_cs_bot.py` 调整为更像真人客服的口径，支持日常寒暄、可感知记忆、减少机械追问。
- 约束：不新增第三方依赖；保持 run_dir 协议与 `scripts/verify_repo.ps1` 唯一验收入口不变。

### DoD Mapping (from request)
- [x] DoD-1: 纯寒暄输入（你好/谢谢/你能做什么等）优先本地响应，不触发工程路由问句。
- [x] DoD-2: 新增 slot-like 会话记忆（`memory_slots`）并在回复中可用于跨轮延续语境。
- [x] DoD-3: 去除默认工程口吻追问（如 patch/verify 路径确认），改为客服自然澄清。
- [x] DoD-4: 增加重复追问抑制，避免同一问题连续多轮重复。
- [x] DoD-5: 增加最小单测覆盖寒暄优先、记忆槽位更新、追问去重。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged: `meta/externals/20260302-telegram-cs-human-memory.md`
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

