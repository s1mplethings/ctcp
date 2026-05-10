# Task Archive - Agent Exchange Experiment And Mainline Integration

## Queue Binding

- Queue Item: `ADHOC-20260509-agent-exchange-experiment-mainline`
- Layer/Priority: `L1 / P0`
- Lane: `Virtual Team Lane`
- Code Changes Allowed: `true`

## Context

The user requested a plan, an experiment, continued optimization, and mainline merge if successful. The task optimizes multi-agent generation by adding a compact role-to-role `agent_exchange` packet instead of relying only on broad prompt prose.

## Scope

In scope:
- `docs/13_agent_exchange_contract.md`
- `docs/12_virtual_team_contract.md`
- `docs/13_contracts_index.md`
- `docs/22_agent_teamnet.md`
- `ctcp_adapters/dispatch_whiteboard.py`
- `ctcp_adapters/agent_exchange_prompt.py`
- `ctcp_adapters/ctcp_artifact_normalizers.py`
- `tests/test_agent_exchange_contract.py`
- task/report metadata

Out of scope:
- provider credentials
- live API/MCP runtime changes
- generated project source
- deterministic project templates/materializers

## Virtual Team Design Summary

- intent: reduce downstream agent drift by making role decisions and context needs explicit.
- product direction: first merge a small optional exchange packet, then defer real context/MCP broker work.
- architecture: carry `agent_exchange` through dispatch request, whiteboard, and api prompt rendering.
- UX/runtime flow: role emits packet, dispatch stores it, next provider prompt consumes it.
- implementation: docs contract, whiteboard sanitizer, prompt renderer, focused tests.
- acceptance: whiteboard persistence, prompt consumption, legacy api-agent suite, canonical verify.
- decision: no live API test in this patch; deterministic propagation is the merge gate.

## Results

- Added `ctcp-agent-exchange-v1` contract.
- `dispatch_whiteboard` now sanitizes and stores optional exchange packets.
- `api_agent` prompts now render `# AGENT_EXCHANGE`.
- Focused tests prove connected + accumulated + consumed.
- Initial implementation was optimized after code-health rejected oversized-file growth.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: `request["agent_exchange"]` reaches dispatch whiteboard and api prompt rendering.
- accumulated: `artifacts/support_whiteboard.json` stores sanitized exchange entries.
- consumed: provider prompts include `# AGENT_EXCHANGE`.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new issue-memory entry for this patch.
- reason: prior source-generation repair tasks already captured the recurring generation failure class; this patch adds runtime contract infrastructure and focused regressions.
- future capture condition: live runs that still lose role-handoff decisions after exchange integration.

## Acceptance Checks

- PASS: `.venv\Scripts\python.exe -m py_compile ctcp_adapters\dispatch_whiteboard.py ctcp_adapters\agent_exchange_prompt.py ctcp_adapters\ctcp_artifact_normalizers.py tests\test_agent_exchange_contract.py`
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_agent_exchange_contract.py" -v`
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py`
- PASS: `.venv\Scripts\python.exe scripts\sync_doc_links.py --check`
- PASS: `.venv\Scripts\python.exe scripts\contract_checks.py`
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py`
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Skill Decision

- skillized: no, because the patch creates runtime contract infrastructure rather than a reusable operator workflow.
- future skill condition: repeated manual authoring or triage of exchange packets.
- persona_lab_impact: none.
