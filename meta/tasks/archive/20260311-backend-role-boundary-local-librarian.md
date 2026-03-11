# Update 2026-03-11 - 后端角色分工收紧与本地 Librarian 硬边界

### Queue Binding
- Queue Item: `ADHOC-20260311-backend-role-boundary-local-librarian`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- Goal: 让 backend dispatch/provider 真正做到“各司其职”，把 `librarian` 与 `contract_guardian` 收回硬本地角色，同时继续让执行角色消费共享 whiteboard 与本地 librarian 线索。
- Scope:
  - 收紧 `scripts/ctcp_dispatch.py` 的 provider resolution，禁止 `mode` / `role_providers` / `CTCP_FORCE_PROVIDER` 把硬本地角色改派到其他 provider。
  - 同步更新 runtime contract docs。
  - 增补 provider selection / live routing 回归，确认 whiteboard 仍能给执行角色使用。
- Out of scope:
  - frontend bridge 或客服文案行为改动。
  - orchestrator 状态机语义变更。
  - 新 provider 接入。

### Task Truth Source (single source for current task)

- task_purpose: 收紧 backend dispatcher 的职责边界，让 `librarian/context_pack` 与 `contract_guardian/review_contract` 始终留在 deterministic local path，同时保留 shared whiteboard + local librarian 对执行角色的上下文支撑。
- allowed_behavior_change:
  - `scripts/ctcp_dispatch.py` 可调整 hard-role provider resolution 与 force-provider 规则。
  - `docs/02_workflow.md`、`docs/22_agent_teamnet.md`、`docs/30_artifact_contracts.md` 可同步更新 contract wording。
  - `tests/test_provider_selection.py`、`tests/test_live_api_only_pipeline.py`、`tests/README_live_api_only.md` 可更新回归与说明。
  - 若 canonical verify 首个失败点落在既有 SimLab fixture 漂移，可最小修复相关 fixture patch 以恢复验收闭环。
  - `meta/backlog/execution_queue.json`、`meta/tasks/CURRENT.md`、`meta/reports/LAST.md` 可记录本轮证据。
- forbidden_goal_shift:
  - 不得把这轮扩展成 dispatcher/provider 大重构。
  - 不得破坏执行角色对 shared whiteboard 的 prompt 注入。
  - 不得让 frontend/customer-facing lane 直接改运行态来规避 backend contract。
- in_scope_modules:
  - `scripts/ctcp_dispatch.py`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `tests/test_provider_selection.py`
  - `tests/test_live_api_only_pipeline.py`
  - `tests/README_live_api_only.md`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `frontend/*`
  - `tools/telegram_cs_bot.py`
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_orchestrate.py`
  - `tools/providers/api_agent.py`
- completion_evidence:
  - `load_dispatch_config` / `dispatch_once` 不再把 `librarian` 或 `contract_guardian` 派发到 `manual_outbox` / `api_agent`。
  - 强制 provider 的情况下，`librarian` 仍能本地生成 `artifacts/context_pack.json`。
  - shared whiteboard 相关 prompt 回归仍通过。

### Analysis / Find (before plan)

- Entrypoint analysis:
  - 运行期入口是 `scripts/ctcp_dispatch.py::dispatch_preview` / `dispatch_once`，由 orchestrator blocked/fail gate 触发。
- Downstream consumer analysis:
  - `local_exec` 消费 `librarian/context_pack` 与 `contract_guardian/review_contract` 请求。
  - `manual_outbox` / `api_agent` 继续消费执行角色 request，并读取 shared whiteboard 上下文。
- Source of truth:
  - hard-role routing 真源是 `scripts/ctcp_dispatch.py` 的 provider resolution。
  - shared whiteboard 真源是 `${run_dir}/artifacts/support_whiteboard.json`。
- Current break point / missing wiring:
  - 当前 dispatcher 仍允许 `mode: manual_outbox` 覆盖 librarian，且 `CTCP_FORCE_PROVIDER` 能把 hard-local role 强推到 `api_agent`，与 runtime contract 冲突。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

### Integration Check (before implementation)

- upstream: orchestrator blocked/fail gate -> `ctcp_dispatch.dispatch_preview/dispatch_once`.
- current_module: hard-role provider resolution in `scripts/ctcp_dispatch.py`.
- downstream: `local_exec.execute` for librarian/contract_guardian; execution-role providers keep consuming `whiteboard` request context。
- source_of_truth: `scripts/ctcp_dispatch.py`, `${run_dir}/artifacts/support_whiteboard.json`, `${run_dir}/artifacts/context_pack.json`.
- fallback: non-hard roles may still use configured provider or forced provider; hard-local roles ignore forced/provider override and stay on `local_exec`.
- acceptance_test:
  - `python -m py_compile scripts/ctcp_dispatch.py tests/test_provider_selection.py tests/test_live_api_only_pipeline.py`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 仅改文档，不改 runtime provider resolution。
  - 靠 `CTCP_FORCE_PROVIDER` 把 local librarian 或 contract_guardian 推成 API role。
  - 为了保住 local librarian 而切断执行角色对白板上下文的消费。
- user_visible_effect:
  - backend 角色分工更稳定，`librarian` 真正保持本地 deterministic。
  - 执行角色仍能收到 whiteboard/librarian 线索，减少上下文断裂。

### DoD Mapping (from execution_queue.json)

- [x] DoD-1: dispatch provider resolution no longer remaps librarian/context_pack or contract_guardian/review_contract away from local_exec via mode, role_providers, or CTCP_FORCE_PROVIDER
- [x] DoD-2: shared whiteboard context remains available to execution roles while local librarian stays usable for deterministic repo-scoped lookup/context_pack generation
- [x] DoD-3: regression coverage proves hard-local role enforcement and whiteboard-assisted provider prompts stay connected

### Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) 先补 queue/CURRENT/LAST，使 archive-pointer 模式下的 workflow gate 重新拥有可检查摘要。
2) 在 `ctcp_dispatch` 收紧 hard-local role 解析，禁止 manual/forced override。
3) 同步更新 runtime contract docs。
4) 补 provider-selection / live-routing 回归，验证 hard-local roles 与 shared whiteboard 并存。
5) 执行 local check/fix loop、triplet guard 与 canonical verify，记录首个失败点和最小修复策略。

## Notes / Decisions

- Default choices made: 保留 `mock_agent` 作为显式测试模式例外，不把它算作生产 runtime 绕过。
- Alternatives considered: 继续保留 `manual_outbox` librarian override；拒绝，因为这会把本地 deterministic librarian 退化成可选项，与 `docs/00_CORE.md` 冲突。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本轮先按 contract drift 修复处理；若 verify 仍因 archive split 触发相同 fixture 失配，则在结果里记录为现有基线问题。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a repository-local dispatch contract refinement rather than a reusable multi-repo workflow asset.

## Results

- Files changed:
  - `scripts/ctcp_dispatch.py`
  - `docs/02_workflow.md`
  - `docs/22_agent_teamnet.md`
  - `docs/30_artifact_contracts.md`
  - `tests/test_provider_selection.py`
  - `tests/test_live_api_only_pipeline.py`
  - `tests/README_live_api_only.md`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/archive/20260311-backend-role-boundary-local-librarian.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/archive/20260311-backend-role-boundary-local-librarian.md`
  - `meta/reports/LAST.md`
- Verification summary:
  - `python scripts/workflow_checks.py` (baseline precheck) => `1`
    - first failure point: `meta/tasks/CURRENT.md` missing mandatory 10-step evidence sections after archive-pointer split
    - minimal fix strategy: embed gate-readable active-task/report summaries in `meta/tasks/CURRENT.md` and `meta/reports/LAST.md`
  - `python scripts/workflow_checks.py` (after CURRENT/LAST summary fix) => `0`
  - `python -m py_compile scripts/ctcp_dispatch.py tests/test_provider_selection.py tests/test_live_api_only_pipeline.py` => `0`
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (9 passed)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `git apply --check --whitespace=nowarn tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` => `0`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (first canonical run) => `1`
    - first failure gate: `lite scenario replay`
    - first failure detail: `S16_lite_fixer_loop_pass` rejected stale fix fixture patch against new CURRENT/LAST headers (`PATCH_GIT_CHECK_FAIL`)
    - minimal fix strategy: update `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to current README/CURRENT/LAST headers and verify it with `git apply --check`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (second canonical run) => `1`
    - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-144907` (`passed=14 failed=0`)
    - first failure gate: `python unit tests`
    - first failure detail:
      - `test_support_bot_humanization.SupportBotHumanizationTests.test_full_project_dialogue_replaces_mojibake_with_project_kickoff_reply`
      - `test_support_bot_humanization.SupportBotHumanizationTests.test_send_customer_reply_prefers_detailed_requirement_over_vague_history`
      - `test_support_bot_humanization.SupportBotHumanizationTests.test_send_customer_reply_prefers_understood_with_one_followup`
    - minimal fix strategy: debug the unrelated support-bot humanization baseline separately; this backend patch no longer blocks workflow/lite replay/triplet gates
- Queue status update suggestion (`todo/doing/done/blocked`): `blocked`
