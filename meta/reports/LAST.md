# Demo Report - LAST

## Goal
- Implement TeamNet dispatcher/provider auto-invocation for missing artifacts:
  - local `librarian` auto-exec
  - API-role `manual_outbox` prompt generation
  - outbox budget stop gate
  - outbox refill tracking events
- Add lite regressions for dispatcher behavior.

## Readlist
- `ai_context/00_AI_CONTRACT.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `docs/00_CORE.md`
- `docs/02_workflow.md`
- `docs/22_agent_teamnet.md`
- `docs/30_artifact_contracts.md`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`

## Plan
1. Docs/Spec: add dispatcher/provider and outbox contract sections.
2. Code: add `ctcp_dispatch` + provider modules and orchestrator integration.
3. Tests: add lite scenarios for missing-review outbox and librarian local-exec.
4. Verify: run doc index check, simlab lite suite, and `verify_repo`.
5. Report: update LAST with demo pointers.

## Timeline / Trace Pointer
- External demo run dir:
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260219-163807-orchestrate`
- Demo trace:
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260219-163807-orchestrate\TRACE.md`
- Demo outbox prompt:
  - `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260219-163807-orchestrate\outbox\001_contract_guardian_review_contract.md`
- Demo pointer file:
  - `meta/run_pointers/LAST_RUN.txt`

## Changes
- Unified diff patch bundle:
  - `PATCHES/20260219-teamnet-dispatch.patch`
- Spec/contract docs:
  - `docs/22_agent_teamnet.md`: added dispatcher/provider wiring and boundaries.
  - `docs/30_artifact_contracts.md`: added `dispatch_config` and `outbox/*.md` contracts.
- Dispatcher/provider implementation:
  - `scripts/ctcp_dispatch.py` (new): gate->role/action mapping, config loading, provider dispatch, outbox fulfillment detection.
  - `tools/providers/manual_outbox.py` (new): template-based prompt generation, dedupe, budget stop.
  - `tools/providers/local_exec.py` (new): librarian-only local execution for `context_pack`.
  - `tools/providers/__init__.py` (new).
- Orchestrator integration:
  - `scripts/ctcp_orchestrate.py`:
    - creates `artifacts/dispatch_config.json` on `new-run`
    - includes `outbox/` in run layout
    - `advance` dispatches on blocked/fail gates:
      - `LOCAL_EXEC_COMPLETED` / `LOCAL_EXEC_FAILED`
      - `OUTBOX_PROMPT_CREATED`
      - `STOP_BUDGET_EXCEEDED`
    - `status` now prints:
      - `outbox prompt created: ...` (when present)
      - `STOP: budget_exceeded (...)` (when applicable)
    - tracks refill completion via `OUTBOX_PROMPT_FULFILLED`.
- Prompt templates (new):
  - `agents/prompts/chair_plan_draft.md`
  - `agents/prompts/chair_file_request.md`
  - `agents/prompts/contract_guardian_review.md`
  - `agents/prompts/cost_controller_review.md`
  - `agents/prompts/patchmaker_patch.md`
  - `agents/prompts/fixer_patch.md`
  - `agents/prompts/researcher_find_web.md`
  - `agents/prompts/librarian_context_pack.md`
- Lite regressions:
  - `simlab/scenarios/S12_lite_orchestrate_context_gate.yaml` (updated: pins librarian to manual_outbox for old gate assertion).
  - `simlab/scenarios/S13_lite_dispatch_outbox_on_missing_review.yaml` (new).
  - `simlab/scenarios/S14_lite_dispatch_local_exec_librarian.yaml` (new).
- Task tracking:
  - `meta/tasks/CURRENT.md` updated for this dispatcher task.

## Verify
- `git worktree add d:\\.c_projects\\adc\\ctcp_patch_check_<ts> HEAD`
  - `git -C d:\\.c_projects\\adc\\ctcp_patch_check_<ts> apply --check d:/.c_projects/adc/ctcp/PATCHES/20260219-teamnet-dispatch.patch`
  - result: pass (then worktree removed)
- `python -m py_compile scripts/ctcp_orchestrate.py scripts/ctcp_dispatch.py scripts/ctcp_librarian.py tools/providers/manual_outbox.py tools/providers/local_exec.py`
  - result: pass
- `python scripts/sync_doc_links.py --check`
  - result: `[sync_doc_links] ok`
- `python simlab/run.py --suite lite`
  - result: `{"passed": 6, "failed": 0, ...}`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - result: pass
  - key output:
    - ctest lite: `2/2` passed
    - workflow gate: ok
    - contract checks: ok
    - doc index check: ok
    - lite scenario replay: `{"passed": 6, "failed": 0, ...}`
    - final: `[verify_repo] OK`

## Open Questions
- None.

## Next Steps
1. If needed, add a dedicated lite case for `budget_exceeded` stop behavior.
2. If needed, add richer chair/fixer templates for adjudication and post-failure fix loops.
