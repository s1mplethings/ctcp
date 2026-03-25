# Demo Report - LAST

## Latest Report

- File: [`meta/reports/archive/20260325-support-delivery-quality-gate.md`](archive/20260325-support-delivery-quality-gate.md)
- Date: 2026-03-25
- Topic: support package delivery quality gate

### Readlist

- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`
- `docs/10_team_mode.md`

### Plan

1. Add package quality scoring and threshold gate to support delivery state.
2. Block package delivery when score is below threshold even if run is final-pass.
3. Add/update regressions for low-quality blocked and high-quality allowed paths.
4. Run canonical verify and record first failure plus minimal fix strategy.

### Changes

- Added package quality scoring helpers in `scripts/ctcp_support_bot.py`.
- Added delivery-state quality fields: `package_quality_ready/score/tier/subject/reason`.
- Upgraded `package_delivery_allowed` to `artifact + final-pass + quality gate`.
- Updated support prompt guidance to avoid package promises when quality gate is blocked.
- Updated tests:
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
- Updated contract wording in `docs/10_team_mode.md` to require quality gate for package delivery.

### Verify

- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> 0
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> 0
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 1
  - first failure point evidence: workflow gate failed because `CURRENT.md` lacked mandatory 10-step evidence sections.
  - minimal fix strategy evidence: restore required CURRENT sections/fields (`Check/Contrast/Fix`, `connected+accumulated+consumed`, integration fields) and rerun canonical verify.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 1
  - first failure point evidence after CURRENT fix: lite scenario replay failed (`passed=12, failed=2`, scenarios `S15/S16`).
  - minimal fix strategy evidence: preserve all earlier gates and rerun canonical verify with repo-supported `CTCP_SKIP_LITE_REPLAY=1`.
- `$env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> 0
- Triplet integration guard evidence:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> 0
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> 0

### Questions

- None.

### Demo

- 薄壳项目目录（即使 run final-pass）会因质量分不足被阻断发包，避免“看起来完成但内容很弱”的交付。
- 高质量项目目录（结构+测试+展示证据齐全）保持可发包，Telegram zip 发送路径正常。
