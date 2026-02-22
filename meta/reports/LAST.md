# Demo Report - LAST

## Goal
- 新增离线 `mock_agent` provider，覆盖多角色流水线连通测试。
- 新增路由矩阵测试与故障注入鲁棒性测试，确保 provider 记录可审计且无 `provider=n/a` 静默失败。
- 提供统一离线测试入口命令，默认不联网、不依赖 `OPENAI_API_KEY`。

## Readlist
- `ai_context/00_AI_CONTRACT.md`
  - 约束：最小改动、patch-first、优先现有验证命令。
- `README.md`
  - 约束：仓库基础门禁入口是 `scripts/verify_repo.*`。
- `BUILD.md`
  - 约束：默认 headless/lite 路径。
- `PATCH_README.md`
  - 约束：交付需 patch 可应用且验证结果可追溯。
- `TREE.md`
  - 约束：目录结构与索引可审计。
- `docs/03_quality_gates.md`
  - 约束：`verify_repo` 覆盖 workflow/contract/doc-index/tests。
- `ai_context/problem_registry.md`
  - 约束：验证必须可复现、可举证。
- `ai_context/decision_log.md`
  - 约束：偏离流程需记录；本次无额外豁免。
- `scripts/ctcp_dispatch.py`
  - 约束：provider 选择与 fallback 由 dispatcher 统一处理。
- `scripts/ctcp_orchestrate.py`
  - 约束：failure bundle 与 gate 推进由 orchestrator 统一处理。
- `docs/30_artifact_contracts.md`
  - 约束：各角色产物的最小字段契约与验证口径。

## Plan
1) Docs/Spec：更新任务单与报告 Readlist。  
2) Code：新增 `mock_agent` 并最小接入 `ctcp_dispatch`。  
3) Test：实现 `linked_flow_smoke` / `routing_matrix` / `robustness_fault_injection`。  
4) Verify：运行统一测试入口与 `scripts/verify_repo.ps1`。  
5) Report：回填改动清单、关键输出和 demo 指针。  

## Changes
- `tools/providers/mock_agent.py` (new)
  - 新增离线 deterministic provider，覆盖：
    - `chair/planner`：`guardrails.md`、`analysis.md`、`file_request.json`、`PLAN_draft.md`、`PLAN.md`
    - `librarian`：读取 `file_request.json` 生成 `context_pack.json`
    - `contract_guardian`：`review_contract.md`
    - `cost_controller`：`review_cost.md`
    - `patchmaker/fixer`：`diff.patch`
  - 新增 role-scoped fault injection：
    - `drop_output`
    - `corrupt_json`
    - `missing_field`
    - `empty_file`
    - `raise_exception`
    - `invalid_patch`
  - 支持通过环境变量或 dispatch config `providers.mock_agent` 注入 fault。
- `scripts/ctcp_dispatch.py`
  - 新增 provider 类型 `mock_agent`（import + known provider + preview/execute 分发）。
- `tests/test_mock_agent_pipeline.py` (new)
  - `test_linked_flow_smoke`: 完整链路产物存在/可解析 + provider 记录非 `n/a`。
  - `test_routing_matrix`: 默认路由、recipe 覆盖、patchmaker/fixer fallback 矩阵检查，并生成 `routing_matrix_report.json`。
  - `test_robustness_fault_injection`: 20 轮故障注入（6 模式覆盖），可恢复场景补齐链路，不可恢复场景生成 `failure_bundle.zip` + 可读诊断。
- `scripts/run_mock_pipeline_tests.py` (new)
  - 统一测试入口命令脚本。
- `meta/tasks/CURRENT.md`
  - 切换为本次 mock provider 测试任务，并完成 DoD/Acceptance 勾选。
- `meta/reports/LAST.md`
  - 更新为本次连通性/路由/鲁棒性测试闭环报告。

## Verify
- 统一入口（离线）
  - Command:
    - `python scripts/run_mock_pipeline_tests.py`
  - Key Output:
    - `Ran 3 tests ... OK`
    - 包含 `linked_flow_smoke`、`routing_matrix`、`robustness_fault_injection` 三组测试。

- Patch 可应用性自检
  - Command:
    - `git diff -- <changed files> > %TEMP%/ctcp_mock_agent_pipeline.patch`
    - `git apply --check --reverse %TEMP%/ctcp_mock_agent_pipeline.patch`
  - Key Output:
    - `PATCH_CHECK_OK`

- 仓库唯一验收入口
  - Command:
    - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - Key Output:
    - `workflow gate (workflow checks): ok`
    - `plan check: ok`
    - `patch check (scope from PLAN): ok (changed_files=10 max_files=200)`
    - `behavior catalog check: ok`
    - `contract checks: ok`
    - `doc index check: ok`
    - `lite scenario replay: passed=9, failed=0`
    - `python unit tests: Ran 41 tests ... OK`
  - Final Result:
    - `[verify_repo] OK`

## Questions
- None.

## Demo
- Report: `meta/reports/LAST.md`
- Run Pointer: `meta/run_pointers/LAST_RUN.txt`
- External TRACE: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe\TRACE.md`
