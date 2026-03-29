# Task - post-librarian-api-routing

## Queue Binding

- Queue Item: `ADHOC-20260324-post-librarian-api-routing`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: 用户要求“除了 librarian 之外，后续阶段都走同一个 API 中转”。
- Dependency check: `ADHOC-20260324-triplet-runtime-wiring-baseline-repair` = `doing` (runtime baseline repaired; this task only changes dispatch/provider routing policy)。
- Scope boundary: 仅调整 dispatcher provider 选择边界、workflow recipe 默认 provider、相关回归与契约文档，不改 support 对话策略。

## Task Truth Source (single source for current task)

- task_purpose: 将 post-librarian 角色默认路由统一到 `api_agent`，保留 `librarian/context_pack` 为唯一 hard-local。
- allowed_behavior_change: 可更新 `scripts/ctcp_dispatch.py`、`workflow_registry/wf_minimal_patch_verify/recipe.yaml`、`workflow_registry/adlc_self_improve_core/recipe.yaml`、`tests/test_provider_selection.py`、`tests/test_live_api_only_pipeline.py`、`tests/test_mock_agent_pipeline.py`、`tests/README_live_api_only.md`、`simlab/scenarios/S13_lite_dispatch_outbox_on_missing_review.yaml`、`simlab/scenarios/S17_lite_linear_mainline_resolver_only.yaml`、`simlab/scenarios/S19_lite_linear_robustness_tripwire.yaml`、`docs/02_workflow.md`、`docs/22_agent_teamnet.md`、`docs/30_artifact_contracts.md`、`meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/tasks/archive/20260324-post-librarian-api-routing.md`、`meta/reports/LAST.md`、`meta/reports/archive/20260324-post-librarian-api-routing.md`。
- forbidden_goal_shift: 不改 orchestrator gate 语义；不改 librarian context_pack 本地执行；不改 support 文案流程。
- in_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `workflow_registry/wf_minimal_patch_verify/recipe.yaml`
  - `workflow_registry/adlc_self_improve_core/recipe.yaml`
  - `tests/test_provider_selection.py`
  - `tests/test_live_api_only_pipeline.py`
  - `tests/test_mock_agent_pipeline.py`
  - `tests/README_live_api_only.md`
  - `simlab/scenarios/S13_lite_dispatch_outbox_on_missing_review.yaml`
  - `simlab/scenarios/S17_lite_linear_mainline_resolver_only.yaml`
  - `simlab/scenarios/S19_lite_linear_robustness_tripwire.yaml`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-post-librarian-api-routing.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-post-librarian-api-routing.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/`
  - `src/`
  - `include/`
- completion_evidence: `contract_guardian/review_contract` 不再 hard-local；provider 选择回归通过；simlab-lite 与 triplet 合同测试通过；canonical verify 通过。

## Analysis / Find (before plan)

- Entrypoint analysis: provider 绑定入口在 `scripts/ctcp_dispatch.py`（`HARD_ROLE_PROVIDERS` + `_resolve_provider`）。
- Config analysis: workflow recipe 中 `wf_minimal_patch_verify` 与 `adlc_self_improve_core` 存在 `contract_guardian/guardian -> local_exec` 默认，会覆盖用户期望。
- Contract analysis: `docs/02_workflow.md`、`docs/22_agent_teamnet.md`、`docs/30_artifact_contracts.md` 和 `tests/README_live_api_only.md` 仍声明 contract_guardian hard-local，需同步。
- Source of truth: `tests/test_provider_selection.py`、`tests/test_mock_agent_pipeline.py`、`simlab/scenarios/S13/S17/S19`、`scripts/verify_repo.ps1`。
- Current break point / missing wiring: contract_guardian 及后续角色在部分路径仍可落本地 provider，不符合“librarian 之后走 API”目标。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: orchestrator blocked gate -> `ctcp_dispatch.derive_request/load_dispatch_config/_resolve_provider`。
- current_module: hard-local role map + provider fallback strategy + workflow default role providers。
- downstream: dispatch preview/execute provider 选择、mock/live 路由矩阵、simlab-lite 线性主流程断言。
- source_of_truth: provider regression tests, simlab suite, and canonical verify。
- fallback: 若 API provider 不可用，记录首失败点并维持现有 fallback 机制（不越界改 support flow）。
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_providers_e2e.py" -v`
  - `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v`
  - `python simlab/run.py --suite lite`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 不通过改测试掩盖 provider 路由差异
  - 不跳过 triplet 合同命令证据
  - 不跳过 canonical verify 记录
- user_visible_effect: 用户指定 API 中转后，librarian 之后的默认角色链路统一走 API provider。

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: dispatcher hard-local role list keeps only librarian/context_pack and no longer pins contract_guardian/review_contract to local_exec
- [x] DoD-2: workflow recipe defaults and provider-resolution regressions confirm contract_guardian and later execution roles resolve to api_agent under api mode
- [x] DoD-3: routing contract docs and tests are synchronized and scoped verify commands pass with evidence

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local routing scan)
- [x] Code changes allowed (`Post-librarian API routing policy update`)
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind new ADHOC queue item and current task pointer for this routing topic.
2) Change dispatcher hard-local map to librarian-only.
3) Adjust provider fallback so non-librarian local/ollama assignment returns to `api_agent`.
4) Update workflow recipes so contract guardian defaults to `api_agent`.
5) Update provider selection and live-routing tests.
6) Sync workflow/contract docs with librarian-only hard-local rule.
7) Run scoped tests + simlab lite + triplet contract tests and record verify evidence。

## Check / Contrast / Fix Loop Evidence

- check / contrast / fix loop:
  - check-1: `HARD_ROLE_PROVIDERS` includes `contract_guardian`。
  - contrast-1: user expectation is only librarian local, downstream roles use API。
  - fix-1: remove `contract_guardian` from hard-local map。
  - check-2: `_resolve_provider` allows `local_exec` and `ollama_agent` for contract_guardian。
  - contrast-2: post-librarian roles should resolve back to API path。
  - fix-2: restrict those providers to librarian/context_pack and fallback to `api_agent` otherwise。
  - check-3: recipe defaults still set contract_guardian local。
  - contrast-3: default role-provider recipes should align with API-first policy。
  - fix-3: set `contract_guardian/guardian` defaults to `api_agent`。
  - check-4: docs/tests still claim contract_guardian hard-local。
  - contrast-4: declared contract must match runtime provider rules。
  - fix-4: sync docs and regression expectations to librarian-only hard-local。
  - check-5: simlab S13/S17/S19 still assert local `review_contract.md` materialization。
  - contrast-5: guardian now routes via API/manual path and should emit outbox prompt first。
  - fix-5: update those scenarios to assert `contract_guardian/review_contract` outbox prompt, then continue downstream gates。

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: dispatcher and workflow recipes now produce API-first post-librarian routing。
  - accumulated: provider-selection/matrix/simlab regression runs captured updated routing evidence。
  - consumed: triplet contract tests and canonical verify consumed updated routing contract and passed。

## Notes / Decisions

- Default choices made: 统一采用 `api_agent` 作为非 librarian 角色的路由落点；保持 librarian 本地确定性执行。
- Alternatives considered: 保留 contract_guardian 允许 local_exec 显式配置；不采纳（与用户要求“librarian 后都走 API”冲突）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none。
- Issue memory decision: 该改动属于路由策略切换，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded routing-policy patch。
- persona_lab_impact: none。

## Results

- Files changed:
  - `scripts/ctcp_dispatch.py`
  - `workflow_registry/wf_minimal_patch_verify/recipe.yaml`
  - `workflow_registry/adlc_self_improve_core/recipe.yaml`
  - `tests/test_provider_selection.py`
  - `tests/test_live_api_only_pipeline.py`
  - `tests/test_mock_agent_pipeline.py`
  - `tests/README_live_api_only.md`
  - `simlab/scenarios/S13_lite_dispatch_outbox_on_missing_review.yaml`
  - `simlab/scenarios/S17_lite_linear_mainline_resolver_only.yaml`
  - `simlab/scenarios/S19_lite_linear_robustness_tripwire.yaml`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-post-librarian-api-routing.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-post-librarian-api-routing.md`
- Verification summary: provider/unit/simlab/triplet/canonical verify all passed.
- Queue status update suggestion (`todo/doing/done/blocked`): done
