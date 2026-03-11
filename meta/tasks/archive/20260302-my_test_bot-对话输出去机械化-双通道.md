# Update 2026-03-02 - my_test_bot 对话输出去机械化（双通道）

### Context
- 用户反馈 my_test_bot 对话仍夹杂内部事件/文件名（如 `guardrails_written`、`RUN.json`），影响客户体验。
- 目标：默认用户回复只保留负责人口吻三段式；内部细节仅落 run_dir ops/debug 通道。

### DoD Mapping (from request)
- [x] DoD-1: 默认聊天不输出内部 key/path/log 痕迹（`TRACE/outbox/RUN.json/guardrails` 等）。
- [x] DoD-2: 统一用户回复为“结论 -> 方案 -> 下一步（仅 1 个问题）”。
- [x] DoD-3: 引入回复双通道结构（`reply_text/next_question/ops_status`），ops 写入 run_dir 日志。
- [x] DoD-4: 增加显式进度开关：用户发送“查看进度”/`debug`（或 `/debug`）才看里程碑摘要；默认关闭自动推进播报。
- [x] DoD-5: 新增最小单测覆盖净化器与 ops 保留。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

