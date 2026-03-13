# Report 2026-03-12 - support bot 全部用户可见回复走模型

## Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `docs/10_team_mode.md`
- `agents/prompts/support_lead_reply.md`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

## Plan
1) Bind a new support-model-routing task and align CURRENT/LAST scope.
2) Update foundational docs and prompt contract so greetings/smalltalk remain mode-gated but are model-routed.
3) Remove local greeting fast path from support runtime and keep strict provider semantics.
4) Add regressions, run workflow/verify gates, and restart the live bot if verification passes.

## Changes
- pending

## Verify
- pending
- first failure point: `python scripts/workflow_checks.py` initially failed because `meta/reports/LAST.md` had not yet recorded explicit first-failure/minimal-fix evidence for this new task scope.
- minimal fix strategy: write explicit first-failure/minimal-fix lines into `meta/reports/LAST.md`, then rerun workflow checks before the canonical verify chain.

## Questions
- None.

## Demo
- Task card: `meta/tasks/CURRENT.md`
- Task archive: `meta/tasks/archive/20260312-support-all-turns-model-routing.md`
- Report archive: `meta/reports/archive/20260312-support-all-turns-model-routing.md`

## Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `docs/00_CORE.md`, `docs/10_team_mode.md`, `agents/prompts/support_lead_reply.md`, `scripts/ctcp_support_bot.py`
- downstream: conversation mode gate -> configured support provider -> `build_final_reply_doc()` -> `artifacts/support_reply.json`
- source_of_truth: support session `artifacts/support_reply.json` + `artifacts/support_session_state.json`
- fallback: only provider failure/deferred paths may degrade outside the model path
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - `local_smalltalk` success-path replies
  - docs claiming greeting stays local
  - bypassing the configured support model on normal customer-visible turns
- user_visible_effect:
  - greetings/smalltalk share the same model-authored support voice as project turns
  - support mode gating remains intact without local scripted replies

skillized: no, because this is a repository-local support-lane policy/wiring refinement, not a reusable multi-repo workflow asset.
