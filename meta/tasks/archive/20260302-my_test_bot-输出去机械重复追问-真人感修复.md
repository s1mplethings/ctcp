# Update 2026-03-02 - my_test_bot 输出去“机械重复追问”（真人感修复）

### Context
- 用户反馈 my_test_bot 在 blocked 状态会重复发送同类消息，且反复追问“继续自动推进可以吗”，对话观感像脚本循环。
- 目标：保留自动推进能力，但把 blocked 场景改为“聚焦一次关键输入 + 不重复催问 + 输入后立即续推”。

### DoD Mapping (from request)
- [x] DoD-1: `advance blocked` 文案从“自动推进确认问句”改为“当前卡点 + 需要补齐的信息”，不再反复问“可以吗”。
- [x] DoD-2: 同一 blocked 原因短时间内不重复推送同类消息，避免一分钟内多条重复播报。
- [x] DoD-3: 自动推进在 blocked 冷却期内暂停，用户补充新输入后自动清除冷却并继续推进。
- [x] DoD-4: 增加最小单测覆盖（blocked 冷却/去重 + 手动 advance 后不二次自动推进）。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

