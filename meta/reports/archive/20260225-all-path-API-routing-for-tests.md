# Update 2026-02-25 (all-path API routing for tests)

### Goal
- 将默认最小工作流路由切换为 API 路径，用于“所有路径走 API 测试”。

### Changes
- `scripts/ctcp_dispatch.py`
  - 默认 dispatch 配置改为 `mode: api_agent`。
  - 移除默认 `librarian -> local_exec` 映射（改为由 mode/recipe 决定）。
- `workflow_registry/wf_minimal_patch_verify/recipe.yaml`
  - 将 `librarian/contract_guardian/chair/cost_controller/researcher` provider 统一改为 `api_agent`。
  - `cost_hints.api_level` 改为 `high`。
- `workflow_registry/index.json`
  - `wf_orchestrator_only.cost_hint.api_level` 同步改为 `high`。
- `tests/test_provider_selection.py`
  - 默认/recipe 路由预期改为 `api_agent`。
- `tests/test_mock_agent_pipeline.py`
  - 路由矩阵默认与 recipe 场景预期改为 `api_agent`。
  - fallback 测试场景改为 API 路由。

### Verify
- `python -m unittest discover -s tests -p "test_provider_selection.py"` => exit 0
- `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py"` => exit 0
- `python -m unittest discover -s tests -p "test_providers_e2e.py"` => exit 0
- `python simlab/run.py --suite lite` => exit 0
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-115244`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 0
  - replay run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-115247`
  - python unit tests: `Ran 49 tests, OK (skipped=3)`

### Demo
- SimLab summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-115244/summary.json`
- verify replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-115247/summary.json`

