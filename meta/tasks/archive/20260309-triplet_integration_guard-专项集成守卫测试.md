# Update 2026-03-09 - triplet_integration_guard 专项集成守卫测试

### Context
- 用户请求：新增 `triplet_integration_guard` 专项测试，覆盖 runtime wiring、issue memory accumulation、skill consumption 三类仓库级契约。
- 本次目标：新增 3 个可执行测试文件 + 配套 fixtures，确保“存在于仓库”不再被误判为“已接线/已累积/已消费”。

### DoD Mapping (from request)
- [x] DoD-1: 新增 `tests/test_runtime_wiring_contract.py`，覆盖 greeting 不入项目流水线、详细需求进入项目经理模式、front API 调用桥接路径。
- [x] DoD-2: 新增 `tests/test_issue_memory_accumulation_contract.py`，覆盖用户可见失败捕获、重复失败累积、修复后状态回写。
- [x] DoD-3: 新增 `tests/test_skill_consumption_contract.py`，覆盖“skills 目录存在 != 运行时已消费”、claim 必须有 runtime evidence、未 skillize 必须给理由。
- [x] DoD-4: 新增 `tests/fixtures/triplet_guard/*` 作为 deterministic fixture 集。
- [x] DoD-5: 新增 `meta/reports/triplet_integration_guard.md` 精简报告模板（可选项）。
- [x] DoD-6: 执行新增测试与 `scripts/verify_repo.ps1` 并记录首个失败点。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Research logged (if needed): `N/A (repo-local contract tests)`
- [x] Code changes allowed: `Yes（tests + fixtures + meta template）`
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] Demo report updated: `meta/reports/LAST.md`

### Plan
1) 新增 `triplet_guard` fixtures（runtime/issue-memory/skill-contract）。
2) 新增 3 个合同测试文件并复用现有 frontend/front-api/_issue_memory 接口。
3) 定向执行新增测试并确保 deterministic pass。
4) 执行 `scripts/verify_repo.ps1`，记录首个失败点与最小修复建议。
5) 回填 `meta/reports/LAST.md`。

