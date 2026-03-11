# Update 2026-03-02 (my_test_bot 回复乱码防护：编码噪声兜底)

### Goal
- 修复用户对话中偶发 `���` 乱码直接透传的问题，确保用户侧回复保持可读自然语言。

### Readlist
- `AGENTS.md`
- `docs/00_CORE.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `tools/telegram_cs_bot.py`
- `tests/test_telegram_cs_bot_employee_style.py`

### Plan
1) 在用户回复净化链路增加 replacement-char（`�`）检测与剔除。  
2) 在追问归一化阶段增加乱码保护：输入追问含 `�` 时回退默认可读追问。  
3) 增加单测覆盖乱码输入，验证用户通道不再出现 `�`。  
4) 运行 `scripts/verify_repo.ps1` 完整复检并落盘。  

### Changes
- `tools/telegram_cs_bot.py`
  - 新增 `_replacement_char_count(text)`。
  - 更新 `_normalize_next_question(...)`：
    - 先清理 `�`。
    - 若原始追问含 `�`，直接回退 `_default_next_question(lang)`，避免乱码追问透传。
  - 更新 `sanitize_customer_reply_text(...)`：
    - 含大量 `�`（>=2）的行直接丢弃。
    - 其余行剔除残留 `�` 后再进入用户通道。
- `tests/test_telegram_cs_bot_employee_style.py`
  - 新增 `test_reply_payload_filters_mojibake_replacement_chars`：
    - 构造含 `���` 的 reply/next_question。
    - 断言用户最终回复不含 `�`，且 `next_question` 不会保留乱码问题。
- `meta/tasks/CURRENT.md`
  - 新增本次“乱码防护”任务节并回填 DoD/Acceptance。
- `meta/reports/LAST.md`
  - 新增本节审计记录。

### Verify
- `python -m unittest discover -s tests -p "test_telegram_cs_bot_employee_style.py" -v` => exit `0`（14 passed）
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => exit `0`（3 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=11`)
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-221217`（`passed=14 failed=0`）
  - python unit tests: `Ran 90 tests, OK (skipped=3)`

### Questions
- None

### Conclusion
- 用户通道已增加乱码兜底，`���` 类 replacement-char 不再直接发给客户。
- 即使上游 provider 返回乱码追问，也会自动回退为默认可读追问，避免对话体验断裂。

### Demo
- Task: `meta/tasks/CURRENT.md`
- Report: `meta/reports/LAST.md`
- Test file: `tests/test_telegram_cs_bot_employee_style.py`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260302-221217/summary.json`

