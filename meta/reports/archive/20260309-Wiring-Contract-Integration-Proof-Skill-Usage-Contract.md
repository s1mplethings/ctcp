# Update 2026-03-09 - Wiring Contract / Integration Proof / Skill Usage Contract

### Readlist
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `AGENTS.md`

### Plan
1) 在 `docs/00_CORE.md` 新增 runtime wiring、frontend bridge、conversation mode gate 三个硬规则段落。
2) 在 `AGENTS.md` 新增 integration proof、wiring 问题禁止 prompt-only 完成、frontend boundary 规则。
3) 在 `ai_context/00_AI_CONTRACT.md` 新增错误记忆积累、用户可见失败入库、skill 使用义务与 runtime skill 消费声明。
4) 新建 `meta/templates/integration_check.md` 统一模板。
5) 运行 `scripts/verify_repo.ps1` 并记录首个失败点。

### Changes
- `docs/00_CORE.md`
  - 新增 `0.X Runtime Wiring Contract`。
  - 新增 `0.Y Frontend-to-Execution Bridge Rule`。
  - 新增 `0.Z Conversation Mode Gate`。
  - 新增 capability complete 判定硬句（reachability/downstream/regression/skill decision）。
- `AGENTS.md`
  - 新增 `Integration Proof Requirement`（含固定输出字段）。
  - 新增 `No Prompt-Only Completion for Wiring Problems`。
  - 新增 `Frontend Boundary Rule`。
- `ai_context/00_AI_CONTRACT.md`
  - 新增 `Error Memory Accumulation Contract`。
  - 新增 `User-Facing Failure Must Not Stay Local`。
  - 新增 `Skill Usage Contract`。
  - 新增 `Runtime Skill Consumption Declaration`。
  - 新增 capability complete 判定硬句。
- `meta/templates/integration_check.md`（新增）
  - 新增统一 Integration Check 模板（Feature/Wiring/Memory/Skill/Verification/Completion）。

### Verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - passed gates:
    - anti-pollution
    - cmake headless lite configure/build + `ctest`（2/2）
    - workflow / plan / patch / behavior / contract / doc-index checks
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-183023/summary.json`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: `missing expected text: failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: `expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused)
  - S15: 对齐 S15 用例中 outbox/assert 文案与当前失败闭环输出，确保 `failure_bundle.zip` 关键提示在预期路径可见。
  - S16: 同步 `lite_fix_remove_bad_readme_link.patch` 与当前 `README.md` 上下文，恢复期望 `expect_exit=0` 的修复路径。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- Updated contracts:
  - `docs/00_CORE.md`
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
- New template:
  - `meta/templates/integration_check.md`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-183023/summary.json`

