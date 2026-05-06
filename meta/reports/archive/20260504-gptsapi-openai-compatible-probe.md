# Demo Report - GPTSAPI OpenAI-Compatible Probe

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/tasks/CURRENT.md`
- `llm_core/clients/openai_compatible.py`
- `tools/providers/api_agent.py`
- external run `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260504-130857-534547-orchestrate`

## Plan
1. Probe the documented gptsapi base URL and previous `/v1` root.
2. Patch endpoint normalization and retry handling.
3. Verify focused tests and small real API probes.
4. Rerun formal VN generation until source-generation evidence or next blocker.

## Changes
- Normalized gptsapi base URL to `https://api.gptsapi.net`.
- Routed gptsapi auto mode to chat completions.
- Added Cloudflare retry-after handling.
- Added focused regressions.

## Verify
- Passed focused py_compile and unit tests for OpenAI-compatible client/API agent behavior.
- Passed small real `gpt-4o` probe.
- Passed scoped code-health growth guard.
- Passed workflow checks after report/task evidence repair.
- Failed canonical `verify_repo.ps1 -Profile code` at module protection because pre-existing out-of-scope dirty files remain: `docs/03_quality_gates.md`, `frontend/support_reply_policy.py`, `scripts/ctcp_support_bot.py`, and `tests/test_runtime_wiring_contract.py`.
- Formal VN run reached `API:api_agent/source_generation/chunked`.
- Remaining blocker: generated project validation fails because `generate_asset_placeholders` is imported but missing.
- minimal fix strategy evidence: require generated-source cross-file import consistency and rerun the generation repair loop.
- triplet runtime wiring command evidence: formal run proves orchestrator -> dispatch -> `api_agent` -> gptsapi -> provider ledger -> source_generation validation is connected; `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` was not rerun.
- triplet issue memory command evidence: existing external API transport issue memory remains applicable; `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` was not rerun.
- triplet skill consumption command evidence: `.agents/skills/ctcp-workflow/SKILL.md` was consumed; `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` was not rerun.

## Questions
- None.

## Demo
- Source generation now runs through API, but the generated project still needs a repair pass.

## Integration Proof
- completion criteria evidence: `connected + accumulated + consumed`.
- connected: orchestrator used api_agent/gptsapi.
- accumulated: run artifacts recorded request IDs and source report.
- consumed: validation consumed generated source and found the import mismatch.
