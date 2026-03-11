# Update 2026-03-03 - my_test_bot 执行目标对齐（让 bot 知道“要干什么”）

### Context
- 用户明确要求：核心是让 bot 持续知道“当前要干什么”。
- 问题：仅靠自然对话历史会漂移，缺少稳定的“执行目标 + 下一步动作”字段，导致回复偶发泛化。

### DoD Mapping (from request)
- [x] DoD-1: 会话状态新增执行对齐字段：`execution_goal` / `execution_next_action`。
- [x] DoD-2: 每轮真实需求输入会更新执行对齐字段；寒暄输入不污染该字段。
- [x] DoD-3: 回复 prompt 注入 `execution_focus`，强制模型围绕“目标+下一步”组织内容。
- [x] DoD-4: 增加最小单测覆盖执行对齐字段与 prompt 注入行为。
- [x] DoD-5: `scripts/verify_repo.ps1` 全门禁通过。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`docs/10_team_mode.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

