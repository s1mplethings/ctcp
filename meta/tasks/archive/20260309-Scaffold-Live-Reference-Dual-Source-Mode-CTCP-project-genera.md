# Update 2026-03-09 - Scaffold Live-Reference Dual Source Mode (CTCP project generation chain)

### Queue Binding
- Queue Item: `ADHOC-20260309-scaffold-live-reference-mode`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 升级 `scaffold` / `scaffold-pointcloud` 为双模式（`template` + `live-reference`），将 CTCP 母仓库受控导出接入项目生成链与后续 verify/执行链。
- Scope: doc-first 同步文档 + 新增受控导出清单/导出 helper + orchestrate 编排扩展 + 测试补齐 + 验收。
- Out of scope: `new-run/advance/cos-user-v2p` 核心语义重构；provider/manual_outbox 流程重构；整仓镜像导出。

## Task Truth Source (single source for current task)

- task_purpose: 为 CTCP 项目生成链新增 `live-reference` 模式，在不破坏现有模板模式前提下实现白名单受控导出与来源审计。
- allowed_behavior_change:
  - `scaffold`/`scaffold-pointcloud` CLI 新增 `--source-mode` 并在 `live-reference` 分支执行受控导出。
  - 新增 `meta/reference_export_manifest.yaml` 与导出逻辑、来源元数据与报告字段。
  - 扩展项目 manifest 字段与 run_dir 证据字段。
  - 新增/更新相关测试与文档。
- forbidden_goal_shift:
  - 不得改成整仓复制导出。
  - 不得删除现有 template 模式或破坏默认行为。
  - 不得扩大到无关模块重构。
- in_scope_modules:
  - `meta/reference_export_manifest.yaml`
  - `tools/reference_export.py`
  - `scripts/ctcp_orchestrate.py`
  - `README.md`
  - `docs/40_reference_project.md`
  - `docs/30_artifact_contracts.md`
  - `tests/test_scaffold_reference_project.py`
  - `tests/test_scaffold_pointcloud_project.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `src/`, `frontend/` 业务实现、provider 路由链、`scripts/ctcp_dispatch.py`、`scripts/ctcp_front_api.py`。
- completion_evidence:
  - scaffold/template 回归通过；
  - scaffold-pointcloud/template 回归通过；
  - live-reference 新增路径测试通过；
  - `scripts/verify_repo.ps1` 结果记录（PASS 或首个失败点+最小修复）。

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/ctcp_orchestrate.py` 的 `cmd_scaffold` 与 `cmd_scaffold_pointcloud` 为唯一生成入口。
- Downstream consumer analysis:
  - 生成输出由 `cos-user-v2p`、项目内 `scripts/verify_repo.ps1`、后续 CTCP 执行链消费。
  - run_dir 证据由 `TRACE.md`、`events.jsonl`、`artifacts/*report.json` 消费。
- Source of truth:
  - 导出白名单真源：`meta/reference_export_manifest.yaml`。
  - 当前任务范围真源：本文件（`meta/tasks/CURRENT.md`）。
  - 运行契约真源：`docs/00_CORE.md` + verify gate。
- Current break point / missing wiring:
  - 现有 scaffold 仅模板模式，无 live-reference 导出与来源追踪。
  - pointcloud `--force` 当前不是 manifest-only 清理。
  - 缺少 `reference_source.json` 与 source-mode/source-commit 证据字段。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `python scripts/ctcp_orchestrate.py scaffold|scaffold-pointcloud ... --source-mode ...`
- current_module: `scripts/ctcp_orchestrate.py` + `tools/reference_export.py`
- downstream: 生成项目内 `meta/manifest.json`/`manifest.json` + `meta/reference_source.json` + run_dir `scaffold*_report.json`
- source_of_truth: `meta/reference_export_manifest.yaml`（唯一导出白名单）
- fallback: git commit 获取失败时写 `unknown`；非法清单/越界路径/危险清理直接 fail 并写报告错误
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_scaffold_reference_project.py" -v`
  - `python -m unittest discover -s tests -p "test_scaffold_pointcloud_project.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 通过“遍历全仓+黑名单”导出
  - 直接整仓复制（除 `.git` 外全拷）
  - `--force` 删除 manifest 之外未知文件
  - 路径穿越/导出到 repo 内
- user_visible_effect:
  - 用户可显式选择 `template` 或 `live-reference`。
  - live-reference 生成结果含来源 commit、source mode、导出清单与继承统计，可继续执行 verify/cos-user/new-run/advance 链路。

## DoD Mapping (from request)
- [ ] DoD-1: scaffold/scaffold-pointcloud 新增 `--source-mode template|live-reference`，默认 `template`。
- [ ] DoD-2: 新增受版本控制导出清单并作为 live-reference 唯一白名单来源。
- [ ] DoD-3: live-reference 仅按白名单导出，具备路径安全校验与来源 commit 回填。
- [ ] DoD-4: 生成 `meta/reference_source.json`，扩展 manifest/source 字段与 run_dir 报告字段。
- [ ] DoD-5: pointcloud 保持 template 模式兼容，live-reference 可继承 CTCP 规范 + pointcloud 项目文件。
- [ ] DoD-6: 文档与测试同步，verify 结果落盘。

## Acceptance (this update)
- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [x] Doc/spec-first change included in same patch
- [ ] `scripts/verify_repo.*` passes（待本轮执行后回填）
- [ ] `meta/reports/LAST.md` updated in same patch（进行中）

## Plan
1) 先落盘本轮任务与报告计划（bind/read/analyze/integration）。
2) 新增导出清单与导出 helper（白名单、路径校验、copy/transform、exclude/required、source commit）。
3) 改 `ctcp_orchestrate`：接入 source-mode、live-reference 编排、manifest/reference_source/report 字段、manifest-only force 清理。
4) doc-first 更新 `README.md` 与 `docs/40_reference_project.md`，并补 `docs/30_artifact_contracts.md` 新契约字段。
5) 补测试：template 回归 + live-reference 成功路径 + 白名单 + token + 安全边界 + source commit fallback。
6) 执行本地回归 + canonical verify，将结果回填到 `meta/reports/LAST.md`。

## Notes / Decisions
- Default choices made: live-reference 默认导出清单路径为 `meta/reference_export_manifest.yaml`；source commit 获取失败回填 `unknown`。
- Alternatives considered: 直接复用 templates 全量复制；已拒绝（不满足 live-reference 受控导出目标）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为功能扩展，若出现用户可见导出失败将通过新增回归测试固化。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is repository-specific scaffold generation wiring change, not a reusable runtime workflow asset.

## Results (2026-03-09 - Scaffold live-reference dual-mode)

- Files changed:
  - `meta/reference_export_manifest.yaml`
  - `meta/templates/reference_tokens.md`
  - `tools/reference_export.py`
  - `tools/scaffold.py`
  - `scripts/ctcp_orchestrate.py`
  - `README.md`
  - `docs/40_reference_project.md`
  - `docs/30_artifact_contracts.md`
  - `tests/test_scaffold_reference_project.py`
  - `tests/test_scaffold_pointcloud_project.py`
  - `tests/fixtures/reference_export/bad_traversal_source_manifest.yaml`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- DoD completion status:
  - [x] DoD-1: scaffold/scaffold-pointcloud 新增 `--source-mode` 且默认 `template`
  - [x] DoD-2: 新增 `meta/reference_export_manifest.yaml` 作为 live-reference 白名单真源
  - [x] DoD-3: live-reference 导出白名单+路径安全+source commit fallback
  - [x] DoD-4: 生成 `meta/reference_source.json` 并扩展 manifest/report 字段
  - [x] DoD-5: pointcloud template 模式保持回归，live-reference 可生成 CTCP-style 关键输出
  - [ ] DoD-6: canonical verify 全量通过（当前首个失败仍在 lite replay S16，见 `meta/reports/LAST.md`）

- Verification summary:
  - scaffold/scaffold-pointcloud + triplet guard 定向测试通过。
  - `scripts/verify_repo.ps1` 首个失败点：`lite scenario replay / S16_lite_fixer_loop_pass`。

- Queue status update suggestion (`todo/doing/done/blocked`): `blocked` (blocked by pre-existing lite replay S16 fixture convergence on current dirty baseline).

