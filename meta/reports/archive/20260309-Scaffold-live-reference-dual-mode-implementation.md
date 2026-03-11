# Update 2026-03-09 - Scaffold live-reference dual-mode implementation

### Changes
- `meta/reference_export_manifest.yaml` (new)
  - 新增 live-reference 导出白名单真源，按 `scaffold` / `scaffold-pointcloud` + profile 分层定义：
    - `inherit_copy`
    - `inherit_transform`
    - `generate`
    - `exclude`
    - `required_outputs`
- `meta/templates/reference_tokens.md` (new)
  - 稳定 token replacement 输入模板（`PROJECT_NAME/PROJECT_SLUG/UTC_ISO/SOURCE_COMMIT/SOURCE_MODE`）。
- `tools/reference_export.py` (new)
  - 实现受控导出 helper：manifest 读取、路径归一化/边界校验、目录/文件白名单展开、copy/transform 执行、required 输出校验、source commit fallback、manifest-governed force 清理。
- `scripts/ctcp_orchestrate.py`
  - `scaffold` / `scaffold-pointcloud` 新增 `--source-mode template|live-reference`（默认 template）与 `--reference-manifest`（repo-relative，可选）。
  - live-reference 分支接入 `meta/reference_export_manifest.yaml` + `tools/reference_export.py`。
  - 生成 `meta/reference_source.json`，包含 source_mode/source_commit/export_manifest/profile/inherited/generated。
  - 扩展 scaffold / pointcloud manifest 字段：`generated`、`inherited_copy`、`inherited_transform`、`excluded`、`source_commit`、`source_mode`。
  - 扩展 run_dir 证据：plan/report 增加 `source_mode`、`source_commit`、`export_manifest_path`、inherit counts。
  - 强化输出安全：`--force` 改为只清理 manifest 管辖文件，未知文件阻塞。
- `tools/scaffold.py`
  - 收紧 `prepare_output_dir`：无既有 generated manifest 时拒绝 `--force` 清理未知输出。
  - 扩展 `write_output_manifest`，支持 live-reference 元数据字段。
- `README.md`
  - 新增双模式说明与 `scaffold-pointcloud --source-mode live-reference` 示例。
- `docs/40_reference_project.md`
  - 重写为双模式规范：template/live-reference 区别、安全边界、导出清单真源、新元数据、run evidence 扩展、后续流程接续。
- `docs/30_artifact_contracts.md`
  - 新增 scaffold live-reference 元数据契约段。
- `tests/test_scaffold_reference_project.py`
  - 保留 template 回归。
  - 新增 scaffold live-reference 成功路径与 metadata 断言。
  - 新增 source commit fallback (`CTCP_DISABLE_GIT_SOURCE=1`) 断言。
  - 新增 `--force` unmanaged output 防护断言。
- `tests/test_scaffold_pointcloud_project.py`
  - 保留 template 回归。
  - 新增 pointcloud live-reference 成功路径、whitelist 限制、token replacement、report/source metadata 断言。
  - 新增 source commit fallback、repo 内 out 拒绝、unmanaged force 拒绝、traversal manifest 拒绝。
- `tests/fixtures/reference_export/bad_traversal_source_manifest.yaml` (new)
  - 用于路径穿越防护回归。
- `meta/backlog/execution_queue.json`
  - 追加队列项 `ADHOC-20260309-scaffold-live-reference-mode`。
- `meta/tasks/CURRENT.md`
  - 追加本轮 Queue Binding / Task Truth / Analysis / Integration Check / Plan。

### Verify
- `python -m py_compile scripts/ctcp_orchestrate.py tools/scaffold.py tools/reference_export.py tests/test_scaffold_reference_project.py tests/test_scaffold_pointcloud_project.py` => `0`
- `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v` => `0` (4 passed)
- `python -m unittest discover -s tests -p "test_scaffold_pointcloud_project.py" -v` => `0` (7 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (5 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
  - first failure gate: `lite scenario replay`
  - summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-220323/summary.json`
  - failed scenario: `S16_lite_fixer_loop_pass` (`step 6: expect_exit mismatch, rc=1, expect=0`)
  - scenario trace: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260309-220323/S16_lite_fixer_loop_pass/TRACE.md`
  - minimal fix strategy:
    - 修复 S16 依赖的 sandbox verify 通过条件（当前 failure 来自既有 support bot 回归断言不匹配），使 `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` 的修复后路径可在当前基线上重新收敛。

### Demo
- 运行报告：`meta/reports/LAST.md`
- 任务卡：`meta/tasks/CURRENT.md`
- live-reference 示例（pointcloud）:
  - run_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_live_ref_demo_ef941d87549b496a950885442a40ff3c/ctcp_runs/scaffold_pointcloud/20260309-220809-948941-scaffold-pointcloud-demo_v2p`
  - out_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_live_ref_demo_ef941d87549b496a950885442a40ff3c/demo_v2p`
- template 兼容示例（pointcloud）:
  - run_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_template_demo_a4f5ad7e79534c73ab5b5ac0b46182da/ctcp_runs/scaffold_pointcloud/20260309-220820-163078-scaffold-pointcloud-demo_v2p`
  - out_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_template_demo_a4f5ad7e79534c73ab5b5ac0b46182da/demo_v2p`
- live-reference 示例（scaffold）:
  - run_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_scaffold_live_demo_57cc6feb89084235bf762f9f629e6d03/ctcp_runs/ctcp/20260309-220829-067043-scaffold-my_new_proj`
  - out_dir: `C:/Users/sunom/AppData/Local/Temp/ctcp_scaffold_live_demo_57cc6feb89084235bf762f9f629e6d03/my_new_proj`

### Questions
- None.

