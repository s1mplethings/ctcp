# Report 2026-03-12 - support bot 记忆隔离与显式 API 路由锁定

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
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `frontend/conversation_mode_router.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_support_bot_humanization.py`
- `tests/test_runtime_wiring_contract.py`

## Plan
1) Bind the support-memory isolation task and lock scope to `scripts/ctcp_support_bot.py`.
2) Split persistent project brief, per-turn memory, and provider runtime buffer; update routing to classify the current turn first.
3) Restore greeting/smalltalk local fast path and stop explicit API override from falling into `ollama_agent`.
4) Add regressions, run triplet guards plus canonical verify, then record evidence.

## Changes
- `scripts/ctcp_support_bot.py`
  - Split support session state into `project_memory`, `turn_memory`, and `provider_runtime_buffer`.
  - Switched routing to current-turn-first and stopped short follow-ups from reopening `PROJECT_INTAKE`.
  - Added local greeting/smalltalk fast path.
  - Locked explicit provider override to strict route semantics and sanitized mojibake replies before fallback.
- `tests/test_support_bot_humanization.py`
  - Added regressions for local greeting path, project-brief preservation, and strict API override.
- `tests/test_runtime_wiring_contract.py`
  - Added routing contract regression for short follow-up turns.
- `ai_context/problem_registry.md`
  - Added issue-memory entry for support memory bleed and API-to-local semantic drift.
- `meta/backlog/execution_queue.json`, `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`
  - Bound/completed the scoped task and recorded auditable workflow evidence.

## Verify
- `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py` => `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` => `0` (12 passed)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (10 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
- `python scripts/workflow_checks.py` => first run `1`, second run `0`
- first failure point: `python scripts/workflow_checks.py` initially failed because `meta/reports/LAST.md` was missing explicit first-failure/minimal-fix evidence lines.
- minimal fix strategy: add explicit first-failure/minimal-fix evidence to `meta/reports/LAST.md`, then rerun workflow checks and continue the canonical verify chain.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `0`
  - lite replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-120504` (`passed=14 failed=0`)

## Questions
- None.

## Demo
- Task card: `meta/tasks/CURRENT.md`
- Task archive: `meta/tasks/archive/20260312-support-memory-isolation-and-api-route-lock.md`
- Report archive: `meta/reports/archive/20260312-support-memory-isolation-and-api-route-lock.md`
- Canonical verify replay: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260312-120504`
- Live apply: restarted Telegram support bot with the same `api_agent` command line; old PID `4108`, new PID `37308`.

## Integration Proof
- upstream: `scripts/ctcp_support_bot.py::process_message`
- current_module: `scripts/ctcp_support_bot.py`
- downstream: isolated support session state -> provider selection or local fast path -> `build_final_reply_doc()` -> `artifacts/support_reply.json`
- source_of_truth: support session `artifacts/support_session_state.json` + `artifacts/support_reply.json`
- fallback: greeting/smalltalk stays local; explicit provider override failure degrades to manual/customer-facing reply without crossing to another semantic provider
- acceptance_test:
  - `python -m py_compile scripts/ctcp_support_bot.py tests/test_support_bot_humanization.py tests/test_runtime_wiring_contract.py`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - one `task_summary` slot holding both persistent project brief and latest user turn
  - explicit `api_agent` silently falling through to `ollama_agent`
  - greeting depending on provider output
- user_visible_effect:
  - project brief stays stable across short follow-ups
  - greeting stays local and language-stable
  - API-only support routing does not drift into local-model semantics

skillized: no, because this is repository-local support-session state isolation and reply-routing refinement, not a reusable multi-repo workflow asset.
