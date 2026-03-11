# Update 2026-03-04 - 继续扩展 Telegram bot 测试集

### Context
- 用户要求“继续扩展测试集”。
- 目标：在已落地的 `telegram_bot_dataset_v1` 基础上扩展覆盖面（中英文、无 run/有 run、status/outbox/report/decision/advance/cleanup/create-run）。

### DoD Mapping (from request)
- [x] DoD-1: 将 `tests/fixtures/telegram_bot_dataset_v1/cases.jsonl` 扩展到 12+ 条并覆盖多意图分支。
- [x] DoD-2: 新增断言字段与数据集说明保持一致（`contains_any/contains_all/not_contains_any`）。
- [x] DoD-3: 新增数据集通过回归测试，不破坏既有 Telegram 测试。
- [x] DoD-4: 通过 `scripts/verify_repo.ps1` 全门禁验收。

### Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch (`meta/tasks/CURRENT.md`)
- [x] `scripts/verify_repo.ps1` passes
- [x] `meta/reports/LAST.md` updated in same patch

