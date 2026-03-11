# Update 2026-03-01 - USER_NOTES 回显降噪

### Context
- 用户反馈聊天中频繁出现 `已记录到 USER_NOTES: ...`，影响对话连续性。

### DoD Mapping (from request)
- [x] DoD-1: 自然聊天写入 `USER_NOTES` 时默认不回显文件路径。
- [x] DoD-2: 保留可配置能力（`CTCP_TG_NOTE_ACK_PATH=1` 可恢复路径回显）。
- [x] DoD-3: `/note` 显式命令行为保持不变。
- [x] DoD-4: 增加测试覆盖默认静默与可开启回显两种模式。

