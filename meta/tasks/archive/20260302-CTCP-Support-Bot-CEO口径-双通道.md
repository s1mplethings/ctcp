# Update 2026-03-02 - CTCP Support Bot（CEO口径 + 双通道）

### Context
- 用户要求新增一个“更像 CEO/团队负责人”的客服 bot：
  - 对用户只输出自然客服结论，不夹杂任何日志。
  - 对内复用 CTCP provider 体系（本地 ollama / 外部 codex/api）进行分析与执行。
- 约束：不新增第三方依赖；run_dir 必须在仓库外；verify 入口保持 `scripts/verify_repo.*`。

### DoD Mapping (from request)
- [x] DoD-1: 新增 `scripts/ctcp_support_bot.py`，支持 `--stdin` 与 `telegram --token` 两种模式。
- [x] DoD-2: 新增 `agents/prompts/support_lead_reply.md`，强制 JSON 输出和“结论->方案->下一步”口径。
- [x] DoD-3: 新增 `docs/dispatch_config.support_bot.sample.json`，可配置本地 ollama 与外部 codex 路由。
- [x] DoD-4: 实现双通道输出：用户只收 `reply_text`；provider/debug 细节写入 `${run_dir}/logs/support_bot.*.log`。
- [x] DoD-5: 提供离线 `--selftest`，验证 `artifacts/support_reply.json` 产出与回复脱敏规则。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `meta/reports/LAST.md` updated in same patch

