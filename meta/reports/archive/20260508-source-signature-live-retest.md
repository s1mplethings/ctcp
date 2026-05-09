# Demo Report - Live Source Generation Retest After Signature Validation

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-orchestrate-loop/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `scripts/ctcp_orchestrate.py`
- `meta/run_pointers/LAST_RUN.txt`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`

## Plan

1. Bind `ADHOC-20260508-source-signature-live-retest`.
2. Create a fresh concrete phone-to-PC voice assistant generation run.
3. Advance with bounded API usage.
4. Inspect status and source_generation validation evidence.
5. Record first blocker or delivery result.
6. Run metadata closure checks and archive evidence.

## Changes

- Created external run `voice-assistant-signature-retest-20260508`.
- Advanced the CTCP generation chain using `api_agent` / `gpt-4.1`.
- Inspected `source_generation_report.json`, provider ledger, generated-test output, smoke probes, and signature-consistency evidence.
- Recorded regression memory `20260509_001`.

## Verify

- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-signature-retest-20260508 --goal <voice assistant goal>` returned 0 in 0.699 seconds.
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>` returned 0; initial blocker was `waiting for analysis.md`.
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 12` returned 0 in 286.579 seconds and blocked at `generic_validation.passed must be true`.
- TIMEOUT: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 1` timed out after 604.8 seconds. No newer `source_generation_report.json` was written.
- PASS: triplet guard tests returned 0: runtime wiring 25 OK, issue memory 3 OK, skill consumption 3 OK.

## Questions

- None.

## Demo

- Run dir: `%TEMP%\ctcp_runs\ctcp\voice-assistant-signature-retest-20260508`
- Result: not deliverable.
- The new signature validator produced concrete mismatch evidence:
  - `VoiceAssistantService(command_whitelist=...)` vs `VoiceAssistantService(whitelist=...)`
  - `run_server(host=...)` vs `run_server(port=..., service_inst=..., blocking=...)`
  - `CommandRequest(command_text=...)` vs `CommandRequest(command, args)`
- Generated tests also fail because generated runtime code reaches a `NotImplementedError` in an abstract service contract.

## Integration Proof

- connected: orchestrator created and advanced the external run.
- accumulated: run artifacts include provider ledger, source_generation report, generated files, smoke probe results, generated-test output, and signature mismatch rows.
- consumed: this report records the next repair decision: source_generation must plan and reconcile interfaces before/while batching files; continuing raw retries is not enough.

## Issue Memory

- issue memory decision: required and recorded as `20260509_001`.

## First Failure And Repair

- first failure point evidence: source_generation blocked at `artifacts/source_generation_report.json`, reason `generic_validation.passed must be true`.
- minimal fix strategy evidence: improve source_generation batch planning/self-repair to consume `python_signature_consistency` evidence and reject runtime use of abstract stubs raising `NotImplementedError`; do not patch generated source locally or add deterministic templates.

## Skill Decision

- skillized: no, this is a one-off orchestrator retest using the existing `ctcp-orchestrate-loop`.
- persona_lab_impact: none.
