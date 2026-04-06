# Task - project-generation-code-align-md-rules

## Queue Binding

- Queue Item: `ADHOC-20260404-project-generation-code-align-md-rules`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 权威 MD 已经明确 production 与 benchmark 的边界，但当前 project-generation 代码主链仍保留 benchmark sample 内容、弱项目类型判断和未分层 gate，需要按新 MD 对齐实现。
- Dependency check: `ADHOC-20260404-project-generation-contract-mode-separation = done`.
- Scope boundary: 只修 project-generation 主链相关代码、测试与本轮 meta 绑定；不做无关重构。
- Baseline lock: `repo=D:/.c_projects/adc/ctcp`, `branch=main`, `commit=faeaedbd419aeb9de182c606cd7ce27eaa091e89`, `subject=3.3.4`.

## Task Truth Source (single source for current task)

- task_purpose: 让现有 project-generation 代码主链对齐新的 `docs/41_low_capability_project_generation.md`，把固定 benchmark sample 样题从 production 默认逻辑中剥离，并落实 mode、项目类型/交付形态决策、有效 `context_pack` 消费与分层 gate。
- allowed_behavior_change:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/api_agent.py`
  - `scripts/project_generation_gate.py`
  - `scripts/project_manifest_bridge.py`
  - `workflow_registry/wf_project_generation_manifest/recipe.yaml`
  - `tests/manual_backend_interface_narrative_project_runner.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/test_api_agent_templates.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260404-project-generation-contract-mode-separation.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260404-project-generation-contract-mode-separation.md`
- forbidden_goal_shift:
  - 不允许把 fixed narrative benchmark 继续写成 production 默认项目目标。
  - 不允许 benchmark 与 production 共用一套隐式默认行为。
  - 不允许只改测试或只改报告字段而不改主链真实行为。
  - 不允许引入旁路生成器或大规模重构。
- in_scope_modules:
  - `tools/providers/`
  - `scripts/project_generation_gate.py`
  - `scripts/project_manifest_bridge.py`
  - `tests/`
  - `meta/`
- out_of_scope_modules:
  - unrelated support/frontend flows
  - broad workflow refactors
- completion_evidence: 主链 artifacts/manifest/gate/test 都能证明 production 与 benchmark 已分离，固定 benchmark 样例 样题不再充当 production 默认内容，项目类型与交付形态决策能真实影响生成与验收。

## Analysis / Find (before plan)

- Entrypoint analysis: `tools/providers/project_generation_artifacts.py`、`tools/providers/project_generation_business_templates.py`、`scripts/project_generation_gate.py` 和 `scripts/project_manifest_bridge.py` 共同定义了 project-generation 主链的输出契约、业务生成与 gate 语义。
- Downstream consumer analysis: `api_agent` 的 chair action、bridge 的 `get_project_manifest`、manual runner 与 backend 接口测试都会消费这些 artifacts。
- Source of truth: `docs/41_low_capability_project_generation.md` + 当前工作树中的 project-generation 主链代码。
- Current break point / missing wiring: 生产路径里仍有旧样例特化模板与弱判断耦合，mode 未显式入链，`context_pack` 影响和 gate 分层也没有被完整编码。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: 真实用户请求与 benchmark 回归样题仍共享同一条 project-generation workflow，但必须通过 mode 与项目类型决策显式分流。
- current_module: project-generation artifacts/template/gate/manifest/runner/test 主链。
- downstream: backend bridge、验收 gate、manual regression 与后续真实请求都要读取新的 mode/type/shape/runtime evidence。
- source_of_truth: 更新后的 `docs/41_low_capability_project_generation.md` + 代码生成 artifacts。
- fallback: 如果 verify 失败，记录首个失败点和最小修复，不扩散到无关子系统。
- acceptance_test:
  - `python -m unittest tests/test_project_generation_artifacts.py -v`
  - `python -m unittest tests/test_backend_interface_contract_apis.py -v`
  - `python tests/manual_backend_interface_narrative_project_runner.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不只改测试和报告字段却保留原来的 production 默认逻辑。
  - 不把 benchmark 样题继续留在 production 默认语义里。
  - 不用硬编码新的默认项目类型伪装类型决策已实现。
- user_visible_effect: 真实请求会先做项目类型与交付形态决策，benchmark sample 样题只在 benchmark/regression mode 运行，bridge/manifest/gate 会公开反映这些决策与证据。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Production code path no longer treats fixed narrative benchmark content as the default project target, and benchmark sample content is isolated to benchmark/regression mode only.
- [x] DoD-2: Project generation has one explicit project-type plus delivery-shape decision point whose result affects output contract, source generation, startup entry, and verify/gate semantics.
- [x] DoD-3: Runtime artifacts and gates record effective `context_pack` influence plus structural/behavioral/result completion without mixing production acceptance with benchmark acceptance.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Code changes allowed (current worktree already contains preexisting project-generation modifications; this task updates those paths without reverting unrelated edits)
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Archive the contract-only active task/report topic and bind this code-alignment task.
2) Add explicit mode/type/shape decision wiring in the project-generation provider path.
3) Move fixed narrative benchmark behavior behind benchmark-only mode while keeping production generic.
4) Upgrade manifest and gate artifacts to expose effective context influence and layered completion semantics.
5) Update unit/manual regression coverage and run canonical verify.
6) Completion criteria: prove runtime mainline now follows the new MD and no longer treats fixed narrative content as production default behavior.

## Check / Contrast / Fix Loop Evidence

- check-1: current runtime code still resolves project type mostly as `narrative_copilot` vs `generic_copilot`, with no explicit production/benchmark mode in artifacts.
- contrast-1: required target is a runtime mainline where fixed narrative benchmark logic only appears under benchmark/regression mode.
- fix-1: request-derived `execution_mode` / `benchmark_case` became authoritative inside `output_contract_freeze`, so benchmark benchmark sample no longer leaks into production path and production no longer inherits benchmark defaults.
- check-2: current mainline has no unified delivery-shape decision and `context_pack` influence is mostly path-presence gating.
- contrast-2: required target is one explicit decision point whose output affects contract, generation, startup, and verify semantics.
- fix-2: added a unified decision structure in `tools/providers/project_generation_artifacts.py` for `execution_mode + project_type + delivery_shape`, and wired it into output contract, source generation, manifest, deliver, and bridge-visible fields.
- check-3: current gate blocks scaffold-only and missing business files, but does not expose structural/behavioral/result layering as runtime evidence.
- contrast-3: required target is a layered gate model with production-vs-benchmark result criteria.
- fix-3: added layered gate/runtime evidence (`gate_layers`, `behavioral_checks`, `context_influence_summary`) and updated `scripts/project_generation_gate.py` to validate structural, behavioral, and result completion separately.

## Completion Criteria Evidence

- completion criteria: `connected + accumulated + consumed` must all hold before DONE.
- connected: mode split, type/shape decision, generation, manifest/deliver, verify/gates, and regression replay must all carry consistent runtime fields.
- accumulated: project-generation code paths must accumulate the new MD rules into artifacts and tests instead of leaving them in docs only.
- consumed: `context_pack` must prove downstream influence through recorded files plus decision summaries.

## Notes / Decisions

- Default choices made: keep the current workflow and provider layout, add the smallest viable mode/type/shape structures, and avoid introducing a second generation path.
- Alternatives considered: deep refactor into new workflow IDs or new generator stacks (rejected because this task is alignment, not redesign).
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None.
- Issue memory decision: no new issue-memory entry; this patch aligns runtime behavior to an already-updated contract.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes` using `ctcp-workflow` because this is a repo-standard contract-first execution task with required task/report/verify evidence.

## Results

- Files changed:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_source_helpers.py`
  - `tools/providers/api_agent.py`
  - `scripts/project_generation_gate.py`
  - `scripts/project_manifest_bridge.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_backend_interface_contract_apis.py`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `tests/manual_backend_interface_narrative_project_runner.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260404-project-generation-contract-mode-separation.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260404-project-generation-contract-mode-separation.md`
- Verification summary:
  - `$env:PYTHONPATH='.'; python tests/test_project_generation_artifacts.py` -> `0`
  - `python tests/test_backend_interface_contract_apis.py` -> `0`
  - `python tests/test_api_agent_templates.py` -> `0`
  - `python tests/manual_backend_interface_narrative_project_runner.py` -> `1`, first failure point: benchmark request was still downgraded to production because `execution_mode` precedence favored agent output over `frontend_request.constraints`; minimal fix strategy: make request-derived mode/type fields authoritative in `normalize_output_contract_freeze` / `decide_project_generation`
  - `python tests/manual_backend_interface_narrative_project_runner.py` -> `0` after the mode-authority fix and gate probe `rc=0` handling fix
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
  - `python scripts/workflow_checks.py` -> `0`
  - `python simlab/run.py --suite lite` -> `1`, first failure point: `S16_lite_fixer_loop_pass` used an outdated fix patch fixture and got stuck at doc-index recovery; minimal fix strategy: refresh `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to restore README doc-index state and apply against the current task/report headers
  - `python simlab/run.py --suite lite` -> `0` (`passed=14`, `failed=0`) after fixture refresh
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`, first failure point: `project_generation_artifacts.py` exceeded the max-function growth guard; minimal fix strategy: extract helper functions without changing mainline semantics
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`, follow-up failure: lite replay `S16_lite_fixer_loop_pass` still used the outdated fix fixture; minimal fix strategy: repair the fixture patch to restore the README doc index and match the current meta file headers
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- Queue status update suggestion (`todo/doing/done/blocked`):
  - `done`

