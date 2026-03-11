# Update 2026-03-11 - 后端角色分工收紧与本地 Librarian 硬边界

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `docs/02_workflow.md`
- `docs/22_agent_teamnet.md`
- `docs/30_artifact_contracts.md`
- `scripts/ctcp_dispatch.py`
- `tools/providers/local_exec.py`
- `tests/test_provider_selection.py`
- `tests/test_live_api_only_pipeline.py`
- `tests/README_live_api_only.md`
- `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`

### Plan
1) 先让 `CURRENT.md` / `LAST.md` 在 archive-pointer 模式下重新满足 workflow gate 的检查摘要要求。
2) 在 `ctcp_dispatch` 收紧 hard-local role 解析，禁止 `manual_outbox` / `CTCP_FORCE_PROVIDER` 把 librarian/contract_guardian 推离 `local_exec`。
3) 同步更新 runtime contract docs。
4) 补 provider-selection / live-routing 回归，确保 shared whiteboard 仍给执行角色使用。
5) 执行 local check/fix loop、triplet guard、canonical verify，并记录首个失败点与最小修复策略。

### Changes
- `scripts/ctcp_dispatch.py`
  - hard-local roles (`librarian` / `contract_guardian`) no longer yield to `mode`, `role_providers`, or `CTCP_FORCE_PROVIDER`.
  - `live_api_only_violation` no longer misclassifies hard-local roles as provider mismatches.
- `docs/02_workflow.md`
  - hard-local role wording tightened.
- `docs/22_agent_teamnet.md`
  - hard-local role wording tightened.
- `docs/30_artifact_contracts.md`
  - removed librarian manual_outbox option and documented hard-local override ban.
- `tests/test_provider_selection.py`
  - added hard-local provider enforcement coverage plus forced-provider/local librarian integration coverage.
- `tests/test_live_api_only_pipeline.py`
  - live-routing expectations now keep hard-local roles on `local_exec`.
- `tests/README_live_api_only.md`
  - documented that forced api mode still leaves hard-local roles local.
- `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - aligned stale S16 fixer-loop patch to current README/CURRENT/LAST headers so lite replay can apply it cleanly
- `meta/backlog/execution_queue.json`
  - added queue item `ADHOC-20260311-backend-role-boundary-local-librarian`
- `meta/tasks/CURRENT.md`
  - switched active pointer to this backend task and embedded gate-readable summary
- `meta/reports/LAST.md`
  - switched latest report pointer to this backend task and embedded gate-readable summary

### Verify
- `python scripts/workflow_checks.py` (baseline precheck) => `1`
  - first failure point: pointer-style `CURRENT.md` missing mandatory workflow sections
  - minimal fix strategy: embed active-task summary sections in `meta/tasks/CURRENT.md` and matching report summary sections in `meta/reports/LAST.md`
- `python scripts/workflow_checks.py` (rerun) => `0`
- `python -m py_compile scripts/ctcp_dispatch.py tests/test_provider_selection.py tests/test_live_api_only_pipeline.py` => `0`
- `python -m unittest discover -s tests -p "test_provider_selection.py" -v` => `0` (9 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `git apply --check --whitespace=nowarn tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` => `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (first canonical run) => `1`
  - first failure point: `lite scenario replay`
  - minimal fix strategy: align `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch` to current README/CURRENT/LAST headers and verify it with `git apply --check`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (second canonical run) => `1`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260311-144907` (`passed=14 failed=0`)
  - first failure point: `python unit tests`
  - minimal fix strategy:
    - `test_support_bot_humanization.SupportBotHumanizationTests.test_full_project_dialogue_replaces_mojibake_with_project_kickoff_reply`
    - `test_support_bot_humanization.SupportBotHumanizationTests.test_send_customer_reply_prefers_detailed_requirement_over_vague_history`
    - `test_support_bot_humanization.SupportBotHumanizationTests.test_send_customer_reply_prefers_understood_with_one_followup`

### Questions
- None.

### Demo
- Task card: `meta/tasks/CURRENT.md`
- Full task archive: `meta/tasks/archive/20260311-backend-role-boundary-local-librarian.md`
- Full report archive: `meta/reports/archive/20260311-backend-role-boundary-local-librarian.md`
- Runtime entry:
  - `scripts/ctcp_dispatch.py::dispatch_preview`
  - `scripts/ctcp_dispatch.py::dispatch_once`

### Integration Proof
- upstream: orchestrator blocked/fail gate -> `ctcp_dispatch.dispatch_preview/dispatch_once`.
- current_module: hard-role provider resolution in `scripts/ctcp_dispatch.py`.
- downstream: `local_exec.execute` for librarian/contract_guardian; execution-role providers keep consuming `whiteboard` request context.
- source_of_truth: `scripts/ctcp_dispatch.py`, `${run_dir}/artifacts/support_whiteboard.json`, `${run_dir}/artifacts/context_pack.json`.
- fallback: non-hard roles may still use configured provider or forced provider; hard-local roles ignore forced/provider override and stay on `local_exec`.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_provider_selection.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 仅改文档，不改 runtime provider resolution。
  - 靠 `CTCP_FORCE_PROVIDER` 把 local librarian 或 contract_guardian 推成 API role。
  - 为了保住 local librarian 而切断执行角色对白板上下文的消费。
- user_visible_effect: backend 角色分工更稳定，执行角色继续看到 shared whiteboard/librarian 线索，而 local librarian 保持 deterministic local path。
