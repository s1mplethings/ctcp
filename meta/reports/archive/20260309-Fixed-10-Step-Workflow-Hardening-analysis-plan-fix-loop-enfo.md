# Update 2026-03-09 - Fixed 10-Step Workflow Hardening (analysis/plan/fix-loop enforced)

### Readlist
- `docs/00_CORE.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `docs/03_quality_gates.md`
- `meta/templates/integration_check.md`
- `meta/tasks/TEMPLATE.md`
- `scripts/workflow_checks.py`
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- `tools/checks/plan_contract.py`
- `scripts/plan_check.py`

### Plan
1) 先将流程契约统一为固定 10-step，明确 analysis/find -> plan -> implement -> check/fix -> verify。
2) 将 Integration Check / Task 模板字段补齐到可执行流程所需最小集。
3) 在 `scripts/workflow_checks.py` 增加 10-step 关键证据门禁，防止跳步。
4) 在 `scripts/verify_repo.ps1/.sh` 接入 triplet guard gate，作为 canonical verify 的硬子门禁。
5) 回归执行 workflow gate + triplet tests + verify_repo，记录首个失败点与最小修复策略。

### Changes
- `AGENTS.md`
  - 执行顺序由 6 步重构为硬 10-step：bind -> read -> analyze/find -> integration-check -> plan -> spec-first -> implement -> local check/fix loop -> verify -> finalize。
  - step 8 强制 triplet guard 三条命令。
  - DoD gate 覆盖项新增 triplet guard gate。
  - Integration proof 输出字段补齐：`current_module`、`forbidden_bypass`、`user_visible_effect`。
- `docs/00_CORE.md`
  - 新增 `0.W Fixed 10-Step Execution Flow Principle`（简洁硬规则），明确顺序约束与 final verify 位置。
  - DoD gate contract 序列新增 triplet integration guard tests。
- `ai_context/00_AI_CONTRACT.md`
  - 新增 `Fixed 10-Step Workflow Contract`，禁止从 docs 直接跳实现或从实现直接跳最终 verify。
  - 明确 integration completion proof 必须覆盖 `connected + accumulated + consumed`。
- `ai_context/CTCP_FAST_RULES.md`
  - Fast rule 的执行顺序更新为固定 10-step 表达。
- `meta/templates/integration_check.md`
  - Wiring 字段新增 `acceptance_test` 与 `user_visible_effect`。
- `meta/tasks/TEMPLATE.md`
  - 新增 `Analysis / Find` 与 `Integration Check` 必填段。
  - Plan 强制包含 local check/contrast/fix loop、triplet commands、completion criteria。
  - Notes 强化 issue memory decision + skill decision。
- `scripts/workflow_checks.py`
  - 变更检测扩展到 untracked files（避免新增文件绕过 gate）。
  - 任意变更要求同时更新 `meta/tasks/CURRENT.md` 与 `meta/reports/LAST.md`。
  - 增加 10-step 关键证据检查：Analysis/Find、Integration Check、Plan、fix loop、completion criteria、issue memory decision、skill decision。
  - 增加 Integration Check 字段检查：`upstream/current_module/downstream/source_of_truth/fallback/acceptance_test/forbidden_bypass/user_visible_effect`。
  - 增加 LAST 证据检查：Readlist/Plan/Verify/Demo、first failure point、minimal fix strategy、triplet command evidence。
- `scripts/verify_repo.ps1`
  - 新增 `triplet integration guard` gate，执行 3 条 contract tests 并记入 `ExecutedGates`。
- `scripts/verify_repo.sh`
  - 同步新增 triplet integration guard gate。
- `docs/03_quality_gates.md`
  - gate sequence 同步脚本现实：在 contract/doc-index 之后、lite replay 之前增加 triplet gate。
- `meta/tasks/CURRENT.md`
  - 新增本轮 10-step 流程固化任务记录（含 Analysis/Find、Integration Check、Plan、Issue/Skill decision）。
- `meta/reports/LAST.md`
  - 新增本轮审计记录。

### Verify
- `python scripts/workflow_checks.py` => exit `0`
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => exit `0` (5 passed)
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => exit `0` (3 passed)
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => exit `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - observed: triplet integration guard step executed successfully inside verify flow
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-193411/summary.json`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: `step 8: include assertion failed: missing expected text: failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: `step 6: expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused)
  - S15: 对齐 S15 场景 include 断言与当前 failure bundle/outbox 提示文本。
  - S16: 对齐 `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` 与当前 README 基线。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Workflow gate script: `scripts/workflow_checks.py`
- Canonical verify gates: `scripts/verify_repo.ps1`, `scripts/verify_repo.sh`
- Updated contracts/templates:
  - `AGENTS.md`
  - `docs/00_CORE.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `ai_context/CTCP_FAST_RULES.md`
  - `meta/templates/integration_check.md`
  - `meta/tasks/TEMPLATE.md`
  - `docs/03_quality_gates.md`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-193411/summary.json`

