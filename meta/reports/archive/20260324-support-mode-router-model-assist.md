# Report - support-mode-router-model-assist

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/TEMPLATE.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

## Plan

1. Bind a new ADHOC support task for model-assisted mode arbitration.
2. Keep rule-based mode detection as first pass and add model arbitration only for ambiguous turns.
3. Route arbitration providers with api-first and local fallback.
4. Add focused regressions for arbitration hit and low-confidence fallback.
5. Update support lane contract note.
6. Run focused checks and canonical verify; record first failure and minimal repair.

## Changes

- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260324-support-mode-router-model-assist.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `docs/10_team_mode.md`

## Verify

- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` -> `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- `$env:PYTHONPATH='tests'; python -m unittest -v test_support_bot_humanization.SupportBotHumanizationTests.test_model_mode_router_can_reclassify_ambiguous_turn_to_status_query test_support_bot_humanization.SupportBotHumanizationTests.test_model_mode_router_falls_back_to_detected_mode_on_low_confidence` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point: `workflow gate (workflow checks)` with `changes detected but meta/reports/LAST.md was not updated`
- minimal fix strategy: update `meta/reports/LAST.md` and archive report topic, then rerun canonical verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point (rerun): `workflow gate (workflow checks)` with `LAST.md missing mandatory workflow evidence: triplet issue memory command evidence; triplet skill consumption command evidence`
- minimal fix strategy (rerun): add both triplet command evidences to `meta/reports/LAST.md`, then rerun canonical verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point (final rerun): `patch check (scope from PLAN)` with `out-of-scope path (Scope-Allow): test_final.py`
- minimal fix strategy (final rerun): remove or relocate unrelated preexisting `test_final.py` from worktree (or explicitly include it in scoped PLAN when intentionally part of this patch), then rerun canonical verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- first failure point (closure rerun): `patch check (scope from PLAN)` with `out-of-scope path (Scope-Allow): test_final.py`
- minimal fix strategy (closure rerun): same as above; remove/move unrelated `test_final.py` (or bind it explicitly) before next verify pass

## Questions

- None.

## Demo

- Support mode routing now supports two-pass arbitration:
  - pass 1: existing deterministic `detect_conversation_mode()`
  - pass 2: model-assisted arbitration for ambiguous/explanation turns on bound runs
- Arbitration constraints:
  - does not add new mode labels
  - uses existing mode set only
  - falls back to detected mode when confidence is low or provider fails
- Provider chain for arbitration follows support provider order (`api_agent` first, local fallback next).

## Integration Proof

- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `maybe_override_conversation_mode_with_model` and support mode-router request path
- downstream: `sync_project_context` / `build_support_prompt` / `build_final_reply_doc`
- source_of_truth: support session state + `artifacts/support_mode_router.provider.json`
- fallback: arbitration failure or low confidence keeps rule-detected mode unchanged
- acceptance_test:
  - `python -m py_compile ...`
  - focused mode-router unittests
  - canonical `scripts/verify_repo.ps1`
- forbidden_bypass:
  - no new mode type introduced
  - no bridge bypass introduced
  - no replacement of rule router by model-only path
- user_visible_effect: ambiguous mode turns are less mechanical while preserving existing support flow boundaries.
