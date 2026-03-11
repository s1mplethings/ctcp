# Update 2026-03-09 - Runtime Wiring / Bridge / Skill Contract Hardening

### Context
- 用户请求：在 `docs/00_CORE.md`、`AGENTS.md`、`ai_context/00_AI_CONTRACT.md` 增补 wiring/integration/skill/error-memory 相关硬规则，并新增统一的 Integration Check 模板。
- 本次范围：docs/meta 合同落盘；不改 `src/ web/ scripts/ tools/ include/` 代码目录。

### DoD Mapping (from request)
- [x] DoD-1: `docs/00_CORE.md` 新增 `0.X Runtime Wiring Contract`、`0.Y Frontend-to-Execution Bridge Rule`、`0.Z Conversation Mode Gate`。
- [x] DoD-2: `AGENTS.md` 新增 `Integration Proof Requirement`、`No Prompt-Only Completion for Wiring Problems`、`Frontend Boundary Rule`。
- [x] DoD-3: `ai_context/00_AI_CONTRACT.md` 新增 Error Memory / User-Facing Failure / Skill Usage / Runtime Skill Consumption 契约。
- [x] DoD-4: 新增模板 `meta/templates/integration_check.md`。
- [x] DoD-5: 落盘本轮任务与报告记录，并执行 `scripts/verify_repo.ps1`。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local contract update)`
- [x] Code changes allowed: `N/A (docs/meta only)`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 先按 user 提案将四类契约段落落盘到目标文件。
2) 新建可复用 `integration_check` 模板。
3) 运行唯一验收入口 `scripts/verify_repo.ps1`。
4) 将 Readlist/Plan/Changes/Verify/Questions/Demo 记录到 `meta/reports/LAST.md`。

