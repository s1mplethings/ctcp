# Report - Agent Exchange Experiment And Mainline Integration

- Date: `2026-05-09`
- Queue Item: `ADHOC-20260509-agent-exchange-experiment-mainline`
- Lane: `Virtual Team Lane`

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `docs/12_virtual_team_contract.md`
- `docs/22_agent_teamnet.md`
- `docs/11_task_progress_dialogue.md`
- `docs/13_contracts_index.md`
- `ctcp_adapters/dispatch_whiteboard.py`
- `ctcp_adapters/ctcp_artifact_normalizers.py`
- `tests/test_api_agent_templates.py`

## Plan
1. Bind the task as a Virtual Team Lane experiment.
2. Record required team-design artifacts before implementation.
3. Add `ctcp-agent-exchange-v1` contract.
4. Wire optional exchange packets through whiteboard and provider prompts.
5. Add deterministic propagation tests.
6. Run focused checks, optimize on first failure, and verify.

## Changes
- Added `docs/13_agent_exchange_contract.md`.
- Linked the contract from Virtual Team, TeamNet, and contract index docs.
- Added sanitized `agent_exchange` persistence in `ctcp_adapters/dispatch_whiteboard.py`.
- Added focused prompt rendering in `ctcp_adapters/agent_exchange_prompt.py`.
- Injected `# AGENT_EXCHANGE` into `api_agent` prompts through `ctcp_artifact_normalizers._render_prompt()`.
- Added `tests/test_agent_exchange_contract.py`.

## Verify
- PASS: `.venv\Scripts\python.exe -m py_compile ctcp_adapters\dispatch_whiteboard.py ctcp_adapters\agent_exchange_prompt.py ctcp_adapters\ctcp_artifact_normalizers.py tests\test_agent_exchange_contract.py` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_agent_exchange_contract.py" -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` returned 0, 22 tests OK.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 1 because oversized files grew.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0 after extraction.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\sync_doc_links.py --check` returned 1 because README doc index needed normalization.
- PASS: `.venv\Scripts\python.exe scripts\sync_doc_links.py --check` returned 0 after sync.
- PASS: `.venv\Scripts\python.exe scripts\contract_checks.py` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 1 because `CURRENT.md` and `LAST.md` were missing required workflow evidence fields during closure.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report/task evidence updates.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile, CMake lite build/ctest, workflow/module/prompt/plan/patch/behavior/contract/doc/code-health/triplet gates, and 531 Python tests OK with 4 skipped. Lite replay was skipped by `CTCP_SKIP_LITE_REPLAY=1`.

## Questions
- None.

## Demo
- Whiteboard test proves exchange packets are sanitized and persisted.
- Prompt test proves provider prompts consume the packet under `# AGENT_EXCHANGE`.
- Legacy api-agent template suite passes without requiring exchange packets.

## Integration Proof
- connected: dispatch request field `agent_exchange`.
- accumulated: `artifacts/support_whiteboard.json` `agent_exchange` entry.
- consumed: `api_agent._render_prompt()` includes `# AGENT_EXCHANGE`.

## First Failure And Repair
- first failure point: code health rejected oversized-file growth.
- minimal repair: extract prompt rendering to a small module and keep mainline integration to a narrow import/call.

## Skill Decision
- skillized: no, because this is runtime contract infrastructure.
- future skill condition: repeated operator workflow for authoring/verifying exchange packets.
- persona_lab_impact: none.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
