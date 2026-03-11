# Update 2026-03-02 - my_test_bot 回复乱码防护（编码噪声兜底）

### Context
- 用户反馈 Telegram 会话中出现明显乱码（`���`）的长段回复，影响客户可读性与信任感。
- 目标：在不改变主流程的前提下，为用户通道增加编码噪声检测与兜底，确保看到的始终是可读文本。

### DoD Mapping (from request)
- [x] DoD-1: 用户回复净化链路可识别并剔除明显编码噪声行（含大量 `�`）。
- [x] DoD-2: 若问题文本或追问出现编码噪声，自动回退为默认可读追问，不向用户暴露乱码。
- [x] DoD-3: 新增最小单测覆盖乱码场景，验证输出不含 `�` 且保留自然客服口径。
- [x] DoD-4: `scripts/verify_repo.ps1` 通过并记录到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

