# Update 2026-03-09 - Scaffold/Pointcloud Dual Source Mode (doc-first kickoff)

### Readlist
- `README.md`
- `docs/00_CORE.md`
- `docs/40_reference_project.md`
- `ai_context/00_AI_CONTRACT.md`
- `tests/test_scaffold_pointcloud_project.py`
- `tests/test_scaffold_reference_project.py`
- `scripts/ctcp_orchestrate.py`
- `tools/scaffold.py`
- `AGENTS.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`

### Purpose/Flow/Task Triple-Check
- Repo purpose source: `docs/01_north_star.md`（contract-first、auditable execution）
- Current lane/subsystem purpose source: `docs/00_overview.md` + `docs/10_team_mode.md`（lane 文档，不重定义 repo purpose）
- Current task purpose source: `meta/tasks/CURRENT.md`（本轮已绑定 `ADHOC-20260309-scaffold-live-reference-mode`）
- Conflict check: no blocking conflict found; proceed with implementation scope in CURRENT.

### Plan
1) Docs/spec/meta first:
   - 新增受控导出清单 `meta/reference_export_manifest.yaml`
   - 在 `README.md` / `docs/40_reference_project.md` / `docs/30_artifact_contracts.md` 明确双模式、边界、安全、元数据与后续流程接续
2) Code:
   - 新增 `tools/reference_export.py` 实现 live-reference 白名单导出
   - 修改 `scripts/ctcp_orchestrate.py` 接入 `--source-mode`、source commit、reference_source、manifest/report 扩展
   - 收紧 pointcloud/scaffold force 清理为 manifest-governed
3) Tests:
   - 保持 template 回归
   - 新增 live-reference 最小路径、白名单、token replacement、路径安全、source commit fallback
4) Verify:
   - `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v`
   - `python -m unittest discover -s tests -p "test_scaffold_pointcloud_project.py" -v`
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
   - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

### Integration Proof (planned)
- upstream: `scripts/ctcp_orchestrate.py` subcommands `scaffold` and `scaffold-pointcloud`
- current_module: `tools/reference_export.py` + scaffold command branches
- downstream: generated project contracts (`manifest` + `meta/reference_source.json`) and run_dir reports (`scaffold_report.json` / `scaffold_pointcloud_report.json`)
- source_of_truth: `meta/reference_export_manifest.yaml`
- fallback: git unavailable -> `source_commit=unknown`; invalid export path/config -> fail-fast with report error
- acceptance_test: scaffold tests + triplet guard + verify_repo
- forbidden_bypass: full-repo mirror copy, traversal paths, force-delete unknown files
- user_visible_effect: user can select source mode while keeping template default and get auditable provenance in generated projects

### Questions
- None.

