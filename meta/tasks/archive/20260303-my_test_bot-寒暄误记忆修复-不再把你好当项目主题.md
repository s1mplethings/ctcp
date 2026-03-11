# Update 2026-03-03 - my_test_bot 寒暄误记忆修复（不再把“你好”当项目主题）

### Context
- 用户反馈对话首句“你好”后，bot 回复“我记得你在推进‘你好’”，明显不符合真人客服语感。
- 根因：会话状态更新时把寒暄文本写入 `user_goal`，后续 `smalltalk_reply` 直接把该值当主题回显。

### DoD Mapping (from request)
- [x] DoD-1: 寒暄文本不再写入 `user_goal`。
- [x] DoD-2: `smalltalk_reply` 对“你好/谢谢/what can you do”等伪主题自动忽略，不回显为“正在推进”。
- [x] DoD-3: 新增回归测试覆盖“寒暄不写目标 + 正常需求可写目标”。
- [x] DoD-4: `scripts/verify_repo.ps1` 全门禁通过。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

