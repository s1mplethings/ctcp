# Update 2026-03-09 - triplet_integration_guard（wiring + issue memory + skill consumption）

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
- `frontend/response_composer.py`
- `frontend/conversation_mode_router.py`
- `scripts/ctcp_front_api.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/_issue_memory.py`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_support_bot_humanization.py`

### Plan
1) 新增 triplet guard fixtures，定义 runtime wiring / issue memory / skill consumption 的可重复输入。
2) 新增 runtime wiring 合同测试，覆盖 conversation mode gate 与 front bridge 调用路径。
3) 新增 issue memory 合同测试，覆盖捕获、重复累积、修复后状态回写。
4) 新增 skill consumption 合同测试，覆盖 claim-evidence 与 non-skillized justification 双路径。
5) 执行新增测试 + `scripts/verify_repo.ps1`，记录结果与首个失败点。

### Changes
- `tests/test_runtime_wiring_contract.py`（新增）
  - Test A1: `"你好"` 输入下必须保持 `GREETING`，不得进入 project planning/missing-info/internal-error rewrite 话术。
  - Test A2: 无人机点云详细需求必须进入 `PROJECT_*` 模式，回复保持项目摘要风格，问题数 1-2 且不回退通用 intake 问句。
  - Test A3: `ctcp_front_api` 的 `new/status/advance` 命令必须调用 `ctcp_new_run/ctcp_get_status/ctcp_advance`（bridge traversal）。
- `tests/test_issue_memory_accumulation_contract.py`（新增）
  - Test B1: 用户可见失败被写入 `issue_memory/errors/latest.json|latest.md|index.jsonl`，并包含 `symptom/likely_trigger/affected_entrypoint/expected_behavior`。
  - Test B2: 同类失败重复触发后，`index.jsonl` 至少保留 recurrence/update 证据，不得静默丢弃。
  - Test B3: 失败后再通过场景，`latest.json` 中 `fix_attempt_status/regression_test_status` 必须更新为修复态。
- `tests/test_skill_consumption_contract.py`（新增）
  - Test C1: `.agents/skills` 目录存在本身不构成 skill runtime consumption 证据。
  - Test C2: 当 `claims_skill_usage=true` 时，必须存在可观测 runtime evidence（日志/报告/trace）绑定到具体 skill。
  - Test C3: 当 `claims_skill_usage=false` 时，必须有 `skillized: no, because ...` 的显式理由，否则判定失败。
- `tests/fixtures/triplet_guard/runtime_wiring_cases.json`（新增）
  - greeting 与 detailed request 固定输入。
- `tests/fixtures/triplet_guard/issue_memory_cases.json`（新增）
  - user-visible failure、repeated failure、post-fix 状态样本。
- `tests/fixtures/triplet_guard/skill_consumption_cases.json`（新增）
  - claimed-without-evidence / claimed-with-evidence / non-skillized-with-reason / non-skillized-without-reason 样本。
- `tests/fixtures/triplet_guard/runtime_skill_trace.txt`（新增）
  - skill runtime evidence 样例。
- `meta/reports/triplet_integration_guard.md`（新增）
  - triplet guard 结果记录模板（runtime wiring / issue memory / skill consumption）。
- `meta/tasks/CURRENT.md`
  - 新增本轮 DoD/Acceptance/Plan 任务更新。
- `meta/reports/LAST.md`
  - 新增本轮审计报告。

### Verify
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => exit `0`
  - result: 5 passed
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => exit `0`
  - result: 3 passed
- `$env:PYTHONPATH='.'; python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => exit `0`
  - result: 3 passed
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - passed gates: anti-pollution / headless lite build+ctest / workflow / plan / patch / behavior / contract / doc-index
  - first failure gate: `lite scenario replay`
  - replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-184924/summary.json`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: `step 8: include assertion failed: missing expected text: failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: `step 6: expect_exit mismatch, rc=1, expect=0`
- Minimal repair strategy (first-failure focused)
  - S15: 对齐 S15 断言与当前 failure bundle 输出文案/路径，确保 `failure_bundle.zip` 关键提示文本可被场景断言命中。
  - S16: 对齐 `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` 与当前 README 上下文，恢复预期 `expect_exit=0`。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task: `meta/tasks/CURRENT.md`
- New triplet guard tests:
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_issue_memory_accumulation_contract.py`
  - `tests/test_skill_consumption_contract.py`
- New fixtures:
  - `tests/fixtures/triplet_guard/runtime_wiring_cases.json`
  - `tests/fixtures/triplet_guard/issue_memory_cases.json`
  - `tests/fixtures/triplet_guard/skill_consumption_cases.json`
  - `tests/fixtures/triplet_guard/runtime_skill_trace.txt`
- Optional report template:
  - `meta/reports/triplet_integration_guard.md`
- Verify replay summary:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-184924/summary.json`

