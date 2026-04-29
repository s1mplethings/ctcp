# Task - Remove Project-Generation Template Chain

## Queue Binding

- Queue Item: `ADHOC-20260426-first-turn-quality-uplift`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: 用户要求“把所有包含模板的删除”，当前先在 project_generation 主线执行模板链路移除。
- Dependency check: `ADHOC-20260426-single-support-project-generation-interface = done`
- Scope boundary: 仅处理 project_generation 的模板物料化调用与模块文件，不扩展到其他 template 机制。

## Task Truth Source (single source for current task)

- task_purpose:
  - 从 `source_generation` 主线移除模板物料化调用。
  - 删除 `project_generation` 模板模块文件，避免再被引用。
  - 将 dispatch 与 JSON 产物标准化收敛为 `api_agent` 单通道，不再本地合成关键 JSON 阶段结果。
- allowed_behavior_change:
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `tests/test_project_generation_artifacts.py`
  - `scripts/ctcp_dispatch.py`
  - `ctcp_adapters/dispatch_request_mapper.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `tests/test_provider_selection.py`
  - `tests/test_ctcp_artifact_normalizers.py`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - 不改 support/telegram/runtime 主链
  - 不引入新的生成策略
- in_scope_modules:
  - source_generation 模板调用点
  - project_generation 模板模块
  - 直接测试导入修复
  - dispatch/provider 强制 `api_agent` 路由
  - artifact normalizer 禁止关键 JSON 本地合成
- out_of_scope_modules:
  - 非 project_generation 的 template 目录/功能
  - UI/bridge/provider 路由语义
- completion_evidence:
  - 代码中不再存在 `project_generation_business_templates` 与 `project_generation_generic_archetypes` 的活跃引用。
  - `source_generation` 不再调用 `materialize_business_files(...)`。
  - 语法检查通过，并记录删除模板后的首个回归失败点。
  - `dispatch_request_mapper` 与 `ctcp_dispatch` 对主角色硬锁 `api_agent`。
  - `ctcp_artifact_normalizers` 对关键 JSON 动作不再本地 normalizer 合成。

## Write Scope / Protection

- Allowed Write Paths:
  - `docs/03_quality_gates.md`
  - `docs/10_team_mode.md`
  - `frontend/delivery_reply_actions.py`
  - `frontend/frontdesk_state_machine.py`
  - `frontend/state_resolver.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_front_bridge_watchdog.py`
  - `scripts/ctcp_dispatch.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `ctcp_adapters/dispatch_request_mapper.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `tests/test_provider_selection.py`
  - `tests/test_ctcp_artifact_normalizers.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_support_to_production_path.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_generic_archetypes.py`
  - `tests/test_project_generation_artifacts.py`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260428-template-chain-removal-pivot.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260428-template-chain-removal-pivot.md`
- Protected Paths:
  - unrelated dirty-worktree files
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `shared dirty-worktree includes frozen-kernel files scripts/ctcp_front_bridge.py and scripts/ctcp_orchestrate.py`
- Forbidden Bypass:
  - 不通过 mock 文案伪装“模板已删除”
  - 不回滚不相关脏文件
- Acceptance Checks:
  - `python -m py_compile tools/providers/project_generation_source_stage.py tools/providers/project_generation_artifacts.py tests/test_project_generation_artifacts.py`
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## Analysis / Find (before plan)

- Entrypoint analysis: `normalize_source_generation_stage` 在循环内直接调用 `materialize_business_files(...)`。
- Downstream consumer analysis: `test_project_generation_artifacts.py` 直接导入 `_launcher_script`（来自模板模块）。
- Source of truth: `AGENTS.md` + 本任务卡。
- Current break point / missing wiring: 移除模板后，source_generation 的业务文件将缺失，相关回归会转为 blocked/error。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: `normalize_source_generation` -> `normalize_source_generation_stage`
- current_module: source stage 模板调用移除 + 模板文件删除
- downstream: validation/gate 与 artifacts 回归会反映模板缺失影响
- source_of_truth: 本任务卡
- fallback: 无模板路径时保留现有 scaffold+validation 结果（pass/blocked 由现有 gate 判定）
- acceptance_test:
  - `python -m py_compile tools/providers/project_generation_source_stage.py tools/providers/project_generation_artifacts.py tests/test_project_generation_artifacts.py`
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不篡改验证脚本
  - 不删除失败测试来“制造通过”
- user_visible_effect: project_generation 主线不再使用模板物料化生成业务文件。

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: support first project turn can pass explicit quality constraints through `ctcp_sync_support_project_turn` into `frontend_request` instead of relying only on keyword inference
- [ ] DoD-2: support first project turn uses deeper default advance steps so the first reply reflects more progressed project state
- [ ] DoD-3: project generation decision logic recognizes explicit first-turn quality flags and lifts build profile to `high_quality_extended` deterministically when requested
- [ ] DoD-4: runtime/docs/tests stay aligned for the single support project-generation interface contract

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): not needed, repo-local sufficient
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` executed and first failure recorded
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1. 归档当前 `CURRENT/LAST`。
2. 移除 source stage 中模板调用。
3. 删除 project_generation 模板模块文件。
4. 修复测试中对模板模块的直接导入。
5. 运行语法检查。
6. 运行 `test_project_generation_artifacts.py`，记录首个失败点。
7. 运行 canonical verify，记录首个失败点。
8. 更新 `meta/reports/LAST.md` 与本任务结果。
9. 记录 completion evidence。
10. 向用户交付变更与风险。

## Check / Contrast / Fix Loop Evidence

- check:
  - 检索到 `materialize_business_files` 仅由 source stage 主线调用。
  - 检索到模板模块在活跃代码中的直接导入点有限（source_stage/artifacts/tests）。
- contrast:
  - 目标是“删除模板链路”，因此需要同时删调用点与模块本体，避免残留可调用入口。
- fix:
  - 删除 `source_generation` 模板调用。
  - 删除模板模块文件。
  - 删除测试对 `_launcher_script` 的导入与对应测试。
  - 强制主角色 provider 硬锁到 `api_agent`。
  - 关键 JSON 动作切换为 `api_agent` 输出直通，禁止本地 normalizer 合成。

## Completion Criteria Evidence

- `tools/providers/project_generation_source_stage.py` 已移除 `materialize_business_files(...)` 调用。
- `tools/providers/project_generation_business_templates.py` 已删除。
- `tools/providers/project_generation_generic_archetypes.py` 已删除。
- `rg` 检索未再发现上述模板模块在活跃 Python 代码中的引用。
- completion criteria: `connected + accumulated + consumed` 已在本任务语境下落实为“调用链断开 + 模板模块删除 + 活跃引用清零”。
- `scripts/ctcp_dispatch.py` 与 `ctcp_adapters/dispatch_request_mapper.py` 已将主角色硬锁 `api_agent`。
- `ctcp_adapters/ctcp_artifact_normalizers.py` 已禁止关键 JSON 动作本地合成（要求 API 返回有效 JSON）。

## Issue Memory Decision Evidence

- issue memory decision: `no_new_issue_memory_entry`（本次为用户直接指令下的单次删除动作，无新增长期策略决策）。

## Skill Decision Evidence

- skill decision: `skillized: no, because this change is a direct repo-local code removal and does not require dedicated skill workflow.`

## Notes / Decisions

- Default choices made: 按“project_generation 主线模板链路”做边界删除，不扩展到全仓所有 template 机制。
- Alternatives considered: 全仓模板全删（风险过高、与当前上下文不匹配），未采用。
- Any contract exception reference:
  - None
- persona_lab_impact: none

## Results

- Files changed:
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py` (deleted)
  - `tools/providers/project_generation_generic_archetypes.py` (deleted)
  - `tests/test_project_generation_artifacts.py`
  - `scripts/ctcp_dispatch.py`
  - `ctcp_adapters/dispatch_request_mapper.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `tests/test_provider_selection.py`
  - `tests/test_ctcp_artifact_normalizers.py`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260428-template-chain-removal-pivot.md`
  - `meta/reports/archive/20260428-template-chain-removal-pivot.md`
- Verification summary:
  - `python -m unittest discover -s tests -p "test_*.py" -v` -> PASS (`Ran 473 tests`, `OK`, `skipped=4`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` 首次失败点为运行目录权限（`D:\ctcp_runs` 无写权限），非代码失败
  - `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> PASS (`[verify_repo] OK`)
- Queue status update suggestion (`todo/doing/done/blocked`): `done`（API-only 主线与模板链路删除目标已完成，门禁通过）
