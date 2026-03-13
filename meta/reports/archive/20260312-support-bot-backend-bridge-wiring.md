# Report 2026-03-12 - support bot 接入 front bridge / shared whiteboard / librarian 后台流

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
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-patch-guard/SKILL.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `docs/10_team_mode.md`
- `scripts/ctcp_support_bot.py`
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_dispatch.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

## Plan
1) Bind the support-bridge wiring task and lock scope in `CURRENT.md`.
2) Expose bridge-safe support context/mutation helpers.
3) Wire support bot project turns into create/bind/advance/query plus whiteboard/librarian prompt injection.
4) Add regressions, run triplet guards, live smoke, and canonical verify.

## Changes
- `scripts/ctcp_support_bot.py`
  - Added `support_session_state.json` tracking.
  - Added conversation-mode based bridge sync for project turns.
  - Injects bound run status and shared whiteboard context into provider prompts.
  - Shapes frontend-visible reply from bridge-returned run state.
- `scripts/ctcp_front_bridge.py`
  - Added `ctcp_get_support_context()` and `ctcp_record_support_turn()`.
- `scripts/ctcp_dispatch.py`
  - Added public whiteboard helpers for support-side bridge use.
- `tests/test_support_bot_humanization.py`
  - Added run-binding/whiteboard injection and bound-status regressions.
- `tests/test_runtime_wiring_contract.py`
  - Added support entrypoint -> bridge -> whiteboard runtime wiring regression.
- `docs/10_team_mode.md`
  - Updated support lane contract to require bridge entry for project turns.
- `ai_context/problem_registry.md`
  - Added issue-memory entry for support entry/backend-flow disconnect.

## Verify
- `python -m py_compile scripts/ctcp_support_bot.py scripts/ctcp_front_bridge.py scripts/ctcp_dispatch.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0`
- `python scripts/workflow_checks.py` => `0`
- live smoke: `python scripts\ctcp_support_bot.py --stdin --chat-id live_bridge_smoke_en --provider ollama_agent` => `0`
  - evidence: support session state bound `run_id=20260312-011651-236563-orchestrate`
  - evidence: prompt injected bound run status and `artifacts/support_whiteboard.json` snapshot
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-012536` (`passed=14 failed=0`)

## Questions
- None.

## Demo
- Support session smoke: `%TEMP%\ctcp_live_support_runs\ctcp\support_sessions\live_bridge_smoke_en\`
- Bound run smoke: `%TEMP%\ctcp_live_support_runs\ctcp\20260312-011651-236563-orchestrate\`

## Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `scripts/ctcp_support_bot.py`, `scripts/ctcp_front_bridge.py`, `scripts/ctcp_dispatch.py`
- downstream: bridge-bound run artifacts / shared whiteboard -> provider request -> `support_reply.json`
- source_of_truth: support session `support_session_state.json` + bound run `RUN.json` / `verify_report.json` / `support_whiteboard.json`
- fallback: non-project turns stay local; bridge/provider failure degrades to customer-facing reply
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py scripts/ctcp_front_bridge.py scripts/ctcp_dispatch.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `python scripts\ctcp_support_bot.py --stdin --chat-id live_bridge_smoke_en --provider ollama_agent`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - support bot direct run-state mutation
  - prompt-only "connected" claims
  - keeping whiteboard/librarian unreachable from support entry
- user_visible_effect:
  - project turns enter real backend flow
  - support replies can reflect real run status and shared whiteboard context
  - smalltalk/non-project turns remain local

skillized: no, because this is repository-local support-entry runtime wiring refinement, not a stable reusable multi-repo workflow asset.
