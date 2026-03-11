# Update 2026-03-04（按要求执行全功能测试：Lite + Full Gate）

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `meta/tasks/CURRENT.md`

### Plan
1) 先跑默认 `scripts/verify_repo.ps1`，确认 Lite 主路径全量通过。  
2) 再跑 `CTCP_FULL_GATE=1` 的 `scripts/verify_repo.ps1`，覆盖 full checks。  
3) 记录两次测试的命令、返回码和关键结果到报告。  

### Changes
- `meta/tasks/CURRENT.md`
  - 新增“全功能测试（Lite + Full Gate）”任务记录。
- `meta/reports/LAST.md`
  - 新增本节审计记录。

### Verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - mode: `LITE`
  - ctest lite: `2/2 passed`
  - workflow/plan/patch/behavior/contract/doc-index checks: all `ok`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-205128`（`passed=14 failed=0`）
  - python unit tests: `Ran 108 tests, OK (skipped=3)`
- `CTCP_FULL_GATE=1 powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `0`
  - mode: `FULL`
  - ctest lite: `2/2 passed`
  - workflow/plan/patch/behavior/contract/doc-index checks: all `ok`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-205739`（`passed=14 failed=0`）
  - python unit tests: `Ran 108 tests, OK (skipped=3)`
  - full checks: `[tests] ok (10 cases)`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`（final recheck after report update）=> exit `0`
  - lite replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-210235`（`passed=14 failed=0`）
  - python unit tests: `Ran 108 tests, OK (skipped=3)`

### Questions
- None

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-205128/summary.json`
- Full replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-205739/summary.json`
- Final recheck summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260304-210235/summary.json`

