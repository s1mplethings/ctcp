# Update 2026-03-01 (仅保留全自动推进 + USER_NOTES 静默)

### Goal
- 固定 Telegram 客服为全自动推进模式：无待决问题时持续自动 `advance`，不再依赖用户发送“继续”。
- 自然聊天记录 `USER_NOTES` 时默认静默，不再频繁回显路径提示。

### Changes
- `tools/telegram_cs_bot.py`
  - `Config.load()` 中 `auto_advance` 固定为 `True`（忽略 `CTCP_TG_AUTO_ADVANCE`）。
  - `_scan_push()` 增加空闲自动推进逻辑：无待决 prompts、非 blocked/终态时每 tick 自动推进一步，并立即二次扫描推送。
  - `_decision_text()` 文案更新：无待决项时明确“我会自动推进”。
  - 新增 `CTCP_TG_NOTE_ACK_PATH`（默认 `0`）：自然聊天 note 分支默认静默写入 `USER_NOTES`，可选恢复路径回显。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 新增 `test_config_load_forces_full_auto`。
  - 新增 `test_scan_push_auto_advance_when_idle`。
  - 既有 `USER_NOTES` 静默/可开启回显测试继续通过。
- `docs/10_team_mode.md`
  - 文档新增“全自动推进”说明与 `CTCP_TG_NOTE_ACK_PATH` 示例。
- `meta/tasks/CURRENT.md`
  - 新增本次“仅保留全自动推进模式” DoD 映射。

### Verify
- `python -m py_compile tools/telegram_cs_bot.py` => exit `0`
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（8 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260301-220516/summary.json` (`passed=14 failed=0`)
  - python unit tests: `Ran 81 tests, OK (skipped=3)`

### Demo
- 现在无需手动发“继续”，在无待决问题时 bot 会自动推进。
- 自然聊天不会再反复出现 `已记录到 USER_NOTES: artifacts/USER_NOTES.md`。
- 如需恢复路径回显：设置 `CTCP_TG_NOTE_ACK_PATH=1`。

