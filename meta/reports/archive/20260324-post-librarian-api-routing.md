# Demo Report - 20260324-post-librarian-api-routing

## Topic

librarian 后续角色统一 API 路由（仅 librarian 保持 hard-local）

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/03_quality_gates.md`
- `docs/22_agent_teamnet.md`
- `docs/30_artifact_contracts.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-post-librarian-api-routing.md`
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

## Plan

1. Remove `contract_guardian` from dispatcher hard-local roles and keep only librarian local.
2. Align recipe defaults so guardian routes to `api_agent`.
3. Update provider selection + mock/live routing expectations.
4. Repair simlab lite scenarios S13/S17/S19 to match new guardian routing contract.
5. Run focused tests, triplet guard commands, simlab suite, and canonical verify.

## Changes

- `scripts/ctcp_dispatch.py`
  - `HARD_ROLE_PROVIDERS` now only keeps `librarian`.
  - non-librarian `local_exec`/`ollama_agent` fallback now routes to `api_agent`.
- `workflow_registry/wf_minimal_patch_verify/recipe.yaml`
  - `contract_guardian` provider changed to `api_agent`.
- `workflow_registry/adlc_self_improve_core/recipe.yaml`
  - `guardian` provider changed to `api_agent`.
- `tests/test_provider_selection.py`
  - assertions updated for librarian-only hard-local behavior.
  - added regression that non-librarian `local_exec` resolves to `api_agent`.
- `tests/test_live_api_only_pipeline.py`
  - expected provider for `review_contract` updated to `api_agent`。
- `tests/test_mock_agent_pipeline.py`
  - routing matrix `recipe_guardian` expected provider updated to `api_agent`。
- `tests/README_live_api_only.md`
  - hard-local wording updated to librarian-only.
- `simlab/scenarios/S13_lite_dispatch_outbox_on_missing_review.yaml`
  - changed from local `review_contract.md` expectation to `contract_guardian/review_contract` outbox prompt expectation.
- `simlab/scenarios/S17_lite_linear_mainline_resolver_only.yaml`
  - changed guardian step assertion to outbox prompt expectation.
- `simlab/scenarios/S19_lite_linear_robustness_tripwire.yaml`
  - changed guardian step assertion to outbox prompt expectation.
- `docs/02_workflow.md`, `docs/22_agent_teamnet.md`, `docs/30_artifact_contracts.md`
  - synchronized hard-local contract text to librarian-only.
- meta tracking updates:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/archive/20260324-post-librarian-api-routing.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260324-post-librarian-api-routing.md`

## Verify

- `python -m unittest discover -s tests -p "test_provider_selection.py" -v` -> `0` (9 passed)
- `python -m unittest discover -s tests -p "test_providers_e2e.py" -v` -> `0` (1 passed)
- `python -m unittest discover -s tests -p "test_live_api_only_pipeline.py" -v` -> `0` (3 skipped, live key not enabled)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0` (20 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0` (3 passed)
- `python simlab/run.py --suite lite` -> `0` (`passed=14`, `failed=0`, run_dir=`C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260324-125425`)
- `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v` -> `0` (4 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-1) -> `1`
  - first failure point: `lite scenario replay` (S13/S17/S19 still expected local review_contract materialization)
  - minimal fix strategy: update those scenarios to assert guardian outbox/API routing evidence.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-2) -> `1`
  - first failure point: `python unit tests` (`test_mock_agent_pipeline::test_routing_matrix` expected `local_exec`)
  - minimal fix strategy: align routing matrix expectation to new guardian `api_agent` contract.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (run-3 final) -> `0`
  - result: full verify pass.

## Questions

- None.

## Demo

- 用户要求“除了 librarian 之外后续都走 API”已落实：
  - `contract_guardian/review_contract` 不再 hard-local。
  - workflow 默认 guardian provider 已改为 `api_agent`。
  - simlab/mainline 和 mock/live 路由断言均已同步并通过。

## Integration Proof

- upstream: orchestrator blocked gate -> dispatcher `derive_request` / `_resolve_provider`.
- current_module: provider hard-local boundary + recipe role providers + scenario assertions.
- downstream: outbox/API review-contract path, simlab mainline progression, verify gate closure.
- source_of_truth: unit/simlab/verify command exit codes and artifacts.
- fallback: first failure captured and fixed incrementally (`lite scenario replay` -> `mock routing matrix` -> pass).
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - no mock-only routing claim
  - no skipping simlab contract updates
  - no skipping canonical verify
- user_visible_effect: dispatch 链路在 librarian 之后默认走 API provider，项目流程不再被 guardian 本地硬锁。
