# Task - First-Turn Project Quality Uplift (Support Mainline)

## Queue Binding

- Queue Item: `ADHOC-20260426-first-turn-quality-uplift`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user希望“第一次对话就生成项目”的质量明显提升，避免首轮生成过浅、图片/结构不匹配的问题。
- Dependency check: `ADHOC-20260426-single-support-project-generation-interface = done`.
- Scope boundary: 在既有单主线基础上，将项目生成与控制链路统一收敛到 API-only（含 librarian/context_pack），移除 review_contract 本地回退，并同步 workflow/provider 合同与回归测试。

## Task Truth Source (single source for current task)

- task_purpose:
  - support 首轮创建项目时通过单入口显式传递高质量约束，而不是只依赖关键词猜测
  - 提升首轮默认推进深度，让首轮回复看到更完整的执行状态
  - 让项目生成决策显式识别首轮质量标记并稳定进入 `high_quality_extended`
  - 修复 project-generation 在非关键词 goal 下 `PLAN_draft` 缺失交付字段导致反复阻塞
  - 修复 support 历史 `support_exports` 截图串图导致“图不对”问题
  - 修复 `contract_guardian/review_contract` 在 `api_agent` 瞬时网络失败时的主线可恢复性，避免长流程项目在评审关口早停
  - 修复截图交付只偏向 GUI 结果图的问题，支持“测试证据图”优先与多图发送
  - 修复“历史/状态查询”被误判为 project-generation 目标导致重复生成默认项目的问题
  - 删除 production narrative 主线固定模板文案，改为 goal/run/api 信号驱动的动态内容
  - 删除 visual evidence fallback 固定模板截图文案，改为动态证据文案
  - 将 `librarian/context_pack` 主线 provider 锁定为 `api_agent`
  - 删除 `contract_guardian/review_contract` 的 `local_exec` 自动恢复路径
  - 同步 formal API-only 规则到 md 合同与 workflow recipe
- allowed_behavior_change:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260426-single-support-project-generation-interface.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260426-single-support-project-generation-interface.md`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_bot.py`
  - `tools/providers/project_generation_decisions.py`
  - `docs/backend_interface_contract.md`
  - `docs/10_team_mode.md`
  - `docs/03_quality_gates.md`
  - `frontend/delivery_reply_actions.py`
  - `frontend/delivery_reply_actions.py`
  - `frontend/frontdesk_state_machine.py`
  - `frontend/state_resolver.py`
  - `scripts/ctcp_front_bridge_watchdog.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_dispatch.py`
  - `tests/test_support_chain_breakpoints.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_provider_selection.py`
  - `tests/test_telegram_runtime_smoke.py`
  - `tests/test_support_virtual_delivery_e2e.py`
  - `tests/manual_backend_interface_narrative_project_runner.py`
  - `tests/test_screenshot_priority_selection.py`
  - `tests/test_support_delivery_user_visible_contract.py`
  - `tests/test_project_generation_artifacts.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `tests/test_ctcp_artifact_normalizers.py`
  - `ctcp_adapters/ctcp_artifact_normalizers.py`
  - `tests/test_ctcp_artifact_normalizers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_source_helpers.py`
  - `scripts/resolve_workflow.py`
  - `tests/test_workflow_dispatch.py`
  - `ctcp_adapters/dispatch_request_mapper.py`
  - `llm_core/dispatch/router.py`
  - `tools/formal_api_lock.py`
  - `workflow_registry/wf_project_generation_manifest/recipe.yaml`
  - `workflow_registry/live_api_all_roles/recipe.yaml`
  - `tests/test_mock_agent_pipeline.py`
  - `tests/test_live_api_only_pipeline.py`
  - `tests/README_live_api_only.md`
  - `docs/00_CORE.md`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `docs/dispatch_config.codex_agent.sample.json`
  - `README.md`
- forbidden_goal_shift:
  - no new support workflow lane
  - no non-support generation architecture rewrite
  - no parallel second mainline
- in_scope_modules:
  - support first-turn run creation payload shaping
  - bridge unified interface payload pass-through
  - generation decision explicit quality-flag recognition
  - plan_draft normalizer route-aware project-generation requirement injection
  - support export discovery active-project isolation
  - dispatch review_contract transient-failure auto-recovery
  - project generation test-evidence screenshot materialization + support delivery test-evidence preference
  - backend interface doc alignment
  - project-generation goal routing false-positive hardening for status/history queries
  - production narrative template-content removal in mainline source generation
  - visual evidence fallback template-card removal in mainline capture wording
  - API-only provider locking across dispatch mainline + workflow recipes + formal lock contract
  - remove contract review local fallback execution and keep fail-fast API result semantics
- out_of_scope_modules:
  - frontend redesign
  - benchmark profile redesign
  - delivery transport protocol changes
- completion_evidence:
  - first support project turn can pass explicit quality constraints to `frontend_request`
  - first-turn default advance step depth increases for newly created run
  - decision layer upgrades to `high_quality_extended` when explicit first-turn quality flag exists
  - project-generation routed run (workflow-based) gets complete PLAN delivery requirement lines even when goal text is generic
  - support screenshot delivery no longer mixes inactive historical export directories
  - review_contract gate no longer auto-recovers to `local_exec`; API failure remains explicit and auditable
  - 用户请求“测试截图”时可优先发送测试证据图，并支持单次最多 5 张截图
  - 历史/状态查询（如“你还有之前你生成的项目吗”）不会再触发新项目生成主线

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260426-single-support-project-generation-interface.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260426-single-support-project-generation-interface.md`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_bot.py`
  - `tools/providers/project_generation_decisions.py`
  - `docs/backend_interface_contract.md`
  - `docs/10_team_mode.md`
  - `docs/03_quality_gates.md`
  - `frontend/delivery_reply_actions.py`
  - `frontend/delivery_reply_actions.py`
  - `frontend/frontdesk_state_machine.py`
  - `frontend/state_resolver.py`
  - `scripts/ctcp_front_bridge_watchdog.py`
  - `scripts/ctcp_orchestrate.py`
  - `scripts/ctcp_dispatch.py`
  - `tests/test_support_chain_breakpoints.py`
  - `tests/test_project_turn_mainline_contract.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_runtime_wiring_contract.py`
  - `tests/test_provider_selection.py`
  - `tests/test_telegram_runtime_smoke.py`
  - `tests/test_support_virtual_delivery_e2e.py`
  - `tests/manual_backend_interface_narrative_project_runner.py`
  - `tests/test_screenshot_priority_selection.py`
  - `tests/test_support_delivery_user_visible_contract.py`
  - `tests/test_project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tools/providers/project_generation_source_helpers.py`
  - `scripts/resolve_workflow.py`
  - `tests/test_workflow_dispatch.py`
  - `ctcp_adapters/dispatch_request_mapper.py`
  - `llm_core/dispatch/router.py`
  - `tools/formal_api_lock.py`
  - `workflow_registry/wf_project_generation_manifest/recipe.yaml`
  - `workflow_registry/live_api_all_roles/recipe.yaml`
  - `tests/test_mock_agent_pipeline.py`
  - `tests/test_live_api_only_pipeline.py`
  - `tests/README_live_api_only.md`
  - `docs/00_CORE.md`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `docs/dispatch_config.codex_agent.sample.json`
  - `README.md`
- Protected Paths:
  - external run artifacts under `%TEMP%/ctcp_runs/*`
  - unrelated dirty-worktree files
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `support runtime + bridge mainline wiring`
- Forbidden Bypass:
  - do not claim quality uplift without explicit signal propagation evidence
  - do not bypass single-interface constraint
- Acceptance Checks:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v`
  - `python -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_telegram_runtime_smoke.py" -v`
  - `python -m unittest discover -s tests -p "test_support_virtual_delivery_e2e.py" -v`
  - `python tests/manual_backend_interface_narrative_project_runner.py`
  - `python -m unittest discover -s tests -p "test_screenshot_priority_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_support_delivery_user_visible_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v`
  - `python -m unittest discover -s tests -p "test_live_api_only_pipeline.py" -v`
  - `python -m unittest discover -s tests -p "test_workflow_dispatch.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`

## Analysis / Find (before plan)

- Entrypoint analysis: support runtime currently通过 `ctcp_sync_support_project_turn` 统一同步，但创建 run 时未显式传质量约束。
- Downstream consumer analysis: `tools/providers/project_generation_decisions.py` 已有高质量判定，但首轮缺稳定显式信号。
- Source of truth: `AGENTS.md`, this task card, `docs/10_team_mode.md`, `docs/backend_interface_contract.md`.
- Current break point / missing wiring: bridge sync create path未透传 `constraints/project_intent/project_spec`；首轮推进步数偏浅。
- Current break point / missing wiring: `PLAN_draft` project-generation要求在非关键词 goal 下缺失；support delivery 会混入历史 export 目录导致截图串图。
- Current break point / missing wiring: `review_contract` 在外部 API 短暂失败时会直接阻塞长流程 run，缺少可审计的最小恢复策略。
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: support conversation mode + first run bind path
- current_module: `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, `scripts/ctcp_dispatch.py`
- downstream: `artifacts/frontend_request.json` + generation decision `build_profile` + `artifacts/PLAN_draft.md` + support delivery screenshot selection
- source_of_truth: queue item `ADHOC-20260426-first-turn-quality-uplift`
- fallback: 保持参数默认可选，未传时兼容旧行为
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_chain_breakpoints.py" -v`
  - `python -m unittest discover -s tests -p "test_project_turn_mainline_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`
- forbidden_bypass:
  - no prompt-only/doc-only claim without runtime parameter flow change
- user_visible_effect:
  - 首轮项目生成默认更厚，首轮可见状态更接近“已实质推进”而非刚创建
  - project-generation 阻塞不会因关键词缺失反复卡在 `PLAN_draft`
  - 交付截图将对应当前项目，不再混入旧项目图片
  - 长流程项目在 `review_contract` API 短时失败后可自动恢复，减少“很快卡住”的体感
  - 用户明确要“测试图”时，不会只发 GUI 图；会优先发测试证据图并可一次发多张

## Check / Contrast / Fix Loop Evidence

- check:
  - inspected support first-turn create path and confirmed `ctcp_sync_support_project_turn` create branch previously did not receive explicit quality payload.
  - inspected generation decision logic and confirmed high-quality lift relied on keyword/constraint heuristics without explicit first-turn support flag handling.
  - inspected formal endurance run provider ledger and found repeated `chair:plan_draft` failures under project-generation gate.
  - inspected support delivery export scanning and found historical `artifacts/support_exports/*` directories were merged into current screenshot candidate set.
  - simulated Telegram customer runs and found one API-provider flow blocked at `review_contract` due to transient transport failure.
- contrast:
  - target behavior requires explicit first-turn quality signal propagation through the single bridge interface and deterministic decision-layer recognition.
  - target behavior requires project-generation PLAN requirements to follow workflow routing, not only goal keywords.
  - target behavior requires screenshot selection to stay bound to active project export directory.
  - target behavior requires long流程在 `review_contract` API 异常时可恢复且可审计，而不是直接早停。
- fix:
  - add optional `constraints/project_intent/project_spec` passthrough on bridge sync create path.
  - add support-side first-turn quality payload builder and pass payload only when first project run is created.
  - add explicit flag recognition in `is_high_quality_extended_signal`.
  - add tests for decision flag lift and support->bridge payload assertions.
  - add route-aware project-generation detection in plan normalizer via `find_result`/gate reason.
  - filter support export scanning to active project export dir and exclude historical `support_exports` paths from generic artifacts scan.
  - add regressions for plan routing and support export isolation.
  - add dispatch-level one-shot auto-recovery: non-formal `contract_guardian/review_contract` fails under `api_agent` then retries `local_exec`, and writes recovered provider into ledger/step-meta/acceptance.
  - add regression proving `api_agent -> local_exec` recovery and review artifact creation.
  - add test-screenshot intent routing (`test_evidence`) and raise screenshot delivery cap to 5.
  - add screenshot priority strategy for test evidence files in delivery selection.
  - materialize generated project test-evidence screenshots under `artifacts/test_screenshots/`.
  - add regressions for test-evidence priority, action synthesis, and source-stage artifact presence.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected:
  - support first-turn create call now connects explicit quality payload to bridge sync interface and create-run request materialization.
- accumulated:
  - decision layer now accumulates explicit first-turn quality flags into deterministic `high_quality_extended` selection.
- consumed:
  - targeted tests assert both decision behavior and support mainline payload usage.
  - provider-selection regression asserts review recovery path and provider attribution.

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: 首轮 support 项目 turn 能通过 `ctcp_sync_support_project_turn` 显式传入高质量约束到 run
- [ ] DoD-2: 首轮创建 run 的默认推进步数提升
- [ ] DoD-3: 决策层识别显式首轮质量标记并稳定进入 `high_quality_extended`
- [ ] DoD-4: 文档与测试同步覆盖上述行为
- [x] DoD-5: project-generation 路由在通用 goal 下也能生成包含交付要求的 `PLAN_draft`
- [x] DoD-6: support 公共交付截图只来自当前项目导出目录，不混入历史导出目录
- [x] DoD-7: `review_contract` 在 API-only 主线下不再自动回退 `local_exec`，失败保持显式并保留 provider 证据
- [x] DoD-8: 默认截图交付在存在测试证据图时进入 `test_evidence` 优先模式（无需用户额外指定），并支持单次最多 5 张
- [x] DoD-9: 历史/状态查询不会被识别为 project-generation 目标，避免重复产出同类默认项目

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A (repo-local)`
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Make plan normalizer infer project-generation requirements from routed workflow evidence (`find_result` / gate reason), not goal keywords only.
2) Keep support delivery export discovery scoped to the active project export directory.
3) Add targeted tests for plan-routing enforcement and export screenshot isolation.
4) Add targeted test and dispatch change for `review_contract` transient failure recovery.
5) Update quality gate doc wording and run targeted acceptance checks.
6) Update `meta/reports/LAST.md`.

## Notes / Decisions

- Default choices made: quality uplift仅作用于 support 首轮创建，避免影响非support或已绑定会话。
- Alternatives considered: 全局默认所有项目 `high_quality_extended`; rejected due to broad regression/cost risk.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - `None`
- Issue memory decision: `no new issue memory entry`
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes (ctcp-workflow discipline)`
- persona_lab_impact: `none`
