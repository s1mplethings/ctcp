# Report Archive - 2026-03-16 - Support 对话场景先分流再回复

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `docs/10_team_mode.md`
- `docs/11_task_progress_dialogue.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `frontend/conversation_mode_router.py`
- `frontend/response_composer.py`
- `scripts/ctcp_support_bot.py`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

## Plan

1. Bind a support conversation-situation routing task.
2. Split capability queries out of generic smalltalk in the shared router.
3. Update reply composition so greeting, capability, project, and status turns do not reuse the same generic shell.
4. Add focused support/frontend regressions for the new split and stale-context guards.
5. Run focused tests, then the canonical verify entrypoint, and record the current result.

## Changes

- `frontend/conversation_mode_router.py`
- `frontend/response_composer.py`
- `scripts/ctcp_support_bot.py`
- `docs/10_team_mode.md`
- `tests/test_frontend_rendering_boundary.py`
- `tests/test_runtime_wiring_contract.py`
- `tests/test_support_bot_humanization.py`
- `ai_context/problem_registry.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-support-conversation-situation-routing.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-support-conversation-situation-routing.md`

## Verify

- `python -m py_compile frontend/conversation_mode_router.py frontend/response_composer.py scripts/ctcp_support_bot.py tests/test_frontend_rendering_boundary.py tests/test_runtime_wiring_contract.py tests/test_support_bot_humanization.py` -> `0`
- `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> `0`
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> `0`
- first `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `1`
- final `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
- first failure point:
  - gate: `workflow gate (workflow checks)`
  - reason: `LAST.md missing mandatory workflow evidence: triplet issue memory command evidence / triplet skill consumption command evidence`
- minimal fix strategy:
  - add the executed triplet command evidence to `meta/reports/LAST.md`
  - rerun canonical `scripts/verify_repo.ps1` once the report is updated
- final verify result:
  - profile: `code`
  - gates executed: `lite`, `workflow_gate`, `plan_check`, `patch_check`, `behavior_catalog_check`, `contract_checks`, `doc_index_check`, `triplet_guard`, `lite_replay`, `python_unit_tests`
  - lite replay summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-180422\summary.json`

## Questions

- None.

## Demo

- repo-local probe: `route_conversation_mode("你是谁")` -> `CAPABILITY_QUERY`
- repo-local probe: `render_frontend_output(... recent_user_messages=["你是谁"])` -> `我是这里的 CTCP support 入口，会先判断这轮是寒暄、能力咨询、项目需求还是进度追问，再按对应链路往下接。你现在可以直接说目标，或者告诉我想改哪条回复/流程。`
- repo-local probe: `render_frontend_output(... recent_user_messages=["你能不能按 CTCP 的方式改前端这块"])` -> `可以。我能按现有 CTCP 边界处理前端表现、桥接内的执行接入和对应回归测试。你直接说想改哪一段界面或哪条回复链路，我先帮你收拢范围再动手。`
- repo-local probe: `render_frontend_output(... recent_user_messages=["现在进度到哪了"])` -> `现在就在往下做。` + project summary
- canonical verify result: `[verify_repo] OK`

## Integration Proof

- upstream: user requested situation-first support dialogue with different replies per situation.
- current_module: support/frontend conversation-mode routing and customer-facing reply composition.
- downstream: support bot visible replies, runtime wiring, and frontend rendering boundary tests.
- source_of_truth: `docs/10_team_mode.md`, router/composer/support-bot code, and focused support/frontend regressions.
- fallback: if canonical verify still fails, record only the first failing gate.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_frontend_rendering_boundary.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not only edit tests or prompts without changing real routing
  - do not let capability/status turns leak into project bridge just to force differentiated text
  - do not fold all non-project replies back into one generic shell
- user_visible_effect: greeting, capability, project, and status turns should produce clearly different entry replies that match the current conversation situation.
