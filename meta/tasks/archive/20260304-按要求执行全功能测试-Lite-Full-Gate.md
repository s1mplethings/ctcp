# Update 2026-03-04 - 按要求执行全功能测试（Lite + Full Gate）

### Context
- 用户要求“按照要求对所有的功能做测试”。
- 按仓库契约，验收入口统一为 `scripts/verify_repo.ps1`，并且 `CTCP_FULL_GATE=1` 需覆盖 full checks 路径。

### DoD Mapping (from request)
- [x] DoD-1: 执行默认 `scripts/verify_repo.ps1`（Lite 路径）并记录完整结果。
- [x] DoD-2: 执行 `CTCP_FULL_GATE=1` 的 `scripts/verify_repo.ps1`（Full 路径）并记录完整结果。
- [x] DoD-3: 将测试命令、返回码和关键输出落盘到 `meta/reports/LAST.md`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed: N/A（本次仅测试与文档记录）
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

