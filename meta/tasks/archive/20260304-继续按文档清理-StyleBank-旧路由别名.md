# Update 2026-03-04 - 继续按文档清理 StyleBank 旧路由别名

### Context
- 用户要求继续“按照 MD 修复项目”。
- 当前代码中 `tools/stylebank.py` 仍保留 `api_handoff/local_reply` 旧路由别名兼容，与当前文档路由契约不一致。

### DoD Mapping (from request)
- [x] DoD-1: 移除 `tools/stylebank.py` 中旧路由别名（`api_handoff`、`local_reply`）兼容映射。
- [x] DoD-2: 保持 StyleBank 的确定性行为不退化（现有测试通过）。
- [x] DoD-3: 通过 `scripts/verify_repo.ps1` 全门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

