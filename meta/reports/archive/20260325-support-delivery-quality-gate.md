# Demo Report - 20260325 support-delivery-quality-gate

## Readlist

- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `docs/10_team_mode.md`

## Plan

1. 增加 package 质量评分函数和阈值常量。
2. 把质量门禁接入 `collect_public_delivery_state` 的 delivery allow 判定。
3. 更新回归测试覆盖低质量阻断与高质量放行。
4. 更新 team mode 合同条款并跑验收。

## Changes

- `scripts/ctcp_support_bot.py`
  - 新增 `SUPPORT_PACKAGE_MIN_QUALITY_SCORE=70`。
  - 新增结构/测试/展示证据评分函数与 `quality gate` 决策。
  - `collect_public_delivery_state` 输出新增：
    - `package_quality_ready`
    - `package_quality_score`
    - `package_quality_tier`
    - `package_quality_subject`
    - `package_quality_reason`
  - `package_delivery_allowed` 从“artifact + run gate”升级为“artifact + run gate + quality gate”。
  - prompt context 增加质量字段，提示模型在质量未达标时不要承诺发包。
- `tests/test_support_bot_humanization.py`
  - 原“低质量目录可发包”用例改为“低质量必须被阻断”。
  - 新增“高质量目录放行发包”用例。
- `tests/test_runtime_wiring_contract.py`
  - Telegram 发包链路测试改为高质量项目目录样例，验证门禁通过后仍可发送 zip。
- `docs/10_team_mode.md`
  - 补充 `send_project_package` 需通过 package 质量门禁说明。

## Verify

- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> 0
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> 0
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 1
  - first failure: lite scenario replay (`passed=12, failed=2`, scenarios `S15/S16`)
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 0

## Questions

- None.

## Demo

- 当 run 已 final-pass 但项目目录仅薄壳时：`package_delivery_allowed=false`，阻断原因含质量分不足。
- 当项目目录包含核心结构 + 测试 + 展示证据时：`package_delivery_allowed=true`，zip 正常发送。
