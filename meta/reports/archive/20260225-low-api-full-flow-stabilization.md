# Update 2026-02-25 (low-api full-flow stabilization)

### Goal
- 在尽量低 API 消耗前提下，打通并稳定 ADLC 全流程联动（dispatch -> patch -> verify），避免环境变量串扰导致误失败。

### Changes
- `scripts/ctcp_orchestrate.py`
  - 新增 `verify_run_env()`，在 verify 阶段强制隔离以下变量：
    - `CTCP_FORCE_PROVIDER`
    - `CTCP_MOCK_AGENT_FAULT_MODE`
    - `CTCP_MOCK_AGENT_FAULT_ROLE`
  - 默认禁用 live API 验证入口变量（除非显式 `CTCP_VERIFY_ALLOW_LIVE_API=1`）：
    - `CTCP_LIVE_API`
    - `OPENAI_API_KEY`
    - `CTCP_OPENAI_API_KEY`
  - verify 调用改为使用 `verify_run_env()`。
- `tools/providers/mock_agent.py`
  - `diff.patch` 目标路径改为按 `run_id` 唯一化（`docs/mock_agent_probe_<run_id>.txt`），避免重复 run 时 `new file` 冲突。
- `tests/test_orchestrate_verify_env.py`
  - 新增单测覆盖 verify 环境隔离逻辑（默认隔离 + 显式允许 live API 两种路径）。

### Verify
- `python -m unittest discover -s tests -p "test_orchestrate_verify_env.py"` => exit 0
- `python -m unittest discover -s tests -p "test_provider_selection.py"` => exit 0
- `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py"` => exit 0
- `python -m unittest discover -s tests -p "test_providers_e2e.py"` => exit 0
- `python simlab/run.py --suite lite` => exit 0
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-113410`
  - summary: `passed=11 failed=0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 0
  - verify replay run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-113619`
  - python unit tests: `Ran 49 tests, OK (skipped=3)`

### First Failure Found During Debug
- 失败点 1：`repo_dirty_before_apply`（orchestrate 在脏仓库中阻止 apply）
  - 最小修复：在 clean worktree 或干净工作区执行 full flow。
- 失败点 2：`CTCP_FORCE_PROVIDER=mock_agent` 污染 verify 阶段 provider 相关单测
  - 最小修复：verify 阶段显式清理 provider/live-api 变量（已实现）。

### Demo
- Report: `meta/reports/LAST.md`
- SimLab run: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-113410/summary.json`
- verify replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260225-114245/summary.json`

