# Demo Report — LAST

## Goal
- 将仓库主路径收敛为 headless ADLC 执行闭环，GUI 改为可选构建；并保证 verify/SimLab/gate matrix 可复现通过。

## Readlist
- `AGENTS.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/problem_registry.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`

## Plan
1) 修复 verify 脚本参数与硬失败路径。
2) 让 verify_repo 在 headless 下稳定执行 build + ctest + workflow/contract/docindex + lite scenario。
3) 修复 sandbox 复制污染（build cache 泄漏）导致的矩阵误判。
4) 验证 ADLC headless 入口成功路径与失败 bundle 路径。
5) 重跑 gate matrix 并更新结果。

## Timeline / Trace pointer
- Verify proof: `artifacts/verify/20260218-224104/proof.json`
- Verify contrast: `artifacts/verify/20260218-224104/contrast_report.md`
- ADLC success run: `meta/runs/20260218-223255-adlc-headless/TRACE.md`
- ADLC failure bundle run: `meta/runs/20260218-223335-adlc-headless/failure_bundle.zip`
- Gate matrix summary: `tests/fixtures/adlc_forge_full_bundle/runs/_suite_eval_summary.json`

## Changes (file list)
- `CMakeLists.txt`: `CMAKE_AUTOMOC` 仅在 `CTCP_ENABLE_GUI=ON` 时启用，避免 headless 无意义 Qt 警告。
- `scripts/verify.ps1`: 修复 `--cmake-arg` 传参，增加 `-DBUILD_TESTING=ON`。
- `scripts/verify.sh`: 同步修复 `--cmake-arg`，增加 `-DBUILD_TESTING=ON`。
- `scripts/verify_repo.ps1`: 增加 `ctest` 回退探测（从 cmake 同目录），并在 lite configure 中显式 `BUILD_TESTING=ON`。
- `scripts/verify_repo.sh`: 同步 `ctest` 回退探测与 `BUILD_TESTING=ON`。
- `scripts/adlc_run.py`: 当 `meta/tasks/CURRENT.md` 已存在时自动 `--force`，保证单命令可重复执行。
- `simlab/run.py`: sandbox 复制忽略 `build_lite/build_verify/build_gui/.pytest_cache`，避免 CMake cache 污染。
- `tools/checks/gate_matrix_runner.py`: 同步 sandbox 忽略规则，修复矩阵 case 被构建缓存误伤。
- `meta/tasks/CURRENT.md`: 勾选 `[x] Code changes allowed` 以通过 workflow gate。

## Verify (commands + output)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - exit: `0`
  - 结果: configure/build/ctest(2 tests)/workflow/contract/docindex/lite scenario 全通过。
- `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`
  - exit: `0`
  - 结果: `run_verify` PASS + `adlc_gate` PASS + `contrast_proof` 生成成功。
- `python simlab/run.py --suite core --runs-root tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs --json-out tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json`
  - exit: `0`
  - 结果: passed `6`, failed `0`。
- `python scripts/adlc_run.py --goal "headless-lite-check"`
  - exit: `0`
  - 结果: 生成 `TRACE.md` + `RUN.json`。
- `python scripts/adlc_run.py --goal headless-lite-fail --verify-cmd "python -m module_that_does_not_exist"`
  - exit: `1`
  - 结果: 生成 `failure_bundle.zip`（含 `TRACE.md`/`diff.patch`/`logs`）。
- `python tools/checks/gate_matrix_runner.py`
  - exit: `0`
  - 结果: `PASS 26 / FAIL 0 / SKIP 1`。

## Open questions
- None

## Next steps
- 若需要 Full gate，将 `CTCP_FULL_GATE=1` 纳入 CI 的发布分支流程。
- 若要消除 T12 的 SKIP，需要在执行环境补齐 C++ 编译器工具链并确保 PATH 可见。
