# Update 2026-03-04（继续按 MD 修复：移除 StyleBank 旧路由别名）

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `meta/tasks/CURRENT.md`
- `tools/stylebank.py`

### Plan
1) Docs/spec-first：先更新任务单，登记本轮“按文档继续清理”目标。  
2) Code：移除 `stylebank` 中旧路由别名兼容映射。  
3) Verify：执行目标单测与 `scripts/verify_repo.ps1`。  
4) Report：落盘本节审计记录。  

### Changes
- `tools/stylebank.py`
  - 删除 `_normalize_intent()` 内 legacy 别名映射：`api_handoff`、`local_reply`、`handoff`。
  - 现仅保留标准化行为：空值 -> `general`，其余返回小写原值。
- `meta/tasks/CURRENT.md`
  - 新增本次任务 Update，并回填验收勾选。
- `meta/reports/LAST.md`
  - 新增本节。

### Verify
- `python -m unittest discover -s tests -p "test_support_router_and_stylebank.py" -v` => exit `0`（5 passed）
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - workflow gate: ok
  - patch check: ok (`changed_files=31`)
  - contract checks: ok
  - doc index check: ok
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-203729`（`passed=14 failed=0`）
  - python unit tests: `Ran 108 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-203729/summary.json`

