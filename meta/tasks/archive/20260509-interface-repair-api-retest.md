# Task - Live API Retest After Interface Repair Loop Hardening

## Queue Binding

- Queue Item: `ADHOC-20260509-interface-repair-api-retest`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [ ] Code changes allowed

## Context

- Why this item now: the previous repair hardened source_generation interface validation and retry feedback; this task runs a fresh bounded API retest to see whether CTCP can now generate a concrete runnable project without local templates or manual generated-source fixes.
- Lane: Delivery Lane.
- Scope boundary: external generation run and evidence inspection only. Do not manually create or repair the generated project.

## Task Truth Source

- task_purpose:
  - Create a fresh external CTCP run for the same concrete phone-to-PC voice assistant goal.
  - Force the critical generation path through `api_agent` using the configured OpenAI-compatible endpoint.
  - Inspect source_generation, generic_validation, provider ledger, and final run status evidence.
- allowed_behavior_change:
  - Metadata/report updates for this API test only.
- forbidden_goal_shift:
  - Do not modify production source code in this task.
  - Do not add local deterministic project templates.
  - Do not manually patch generated project files.
  - Do not change provider credentials, endpoint config, or Telegram bot behavior.
- in_scope_modules:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-interface-repair-api-retest.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-interface-repair-api-retest.md`
  - `issue_memory/modifications.jsonl` only if a recurring/new failure is confirmed
- out_of_scope_modules:
  - provider credentials
  - generated project source files
  - local deterministic materializers/templates
  - production source code
- completion_evidence:
  - new-run, advance, and status command evidence.
  - source_generation report summary.
  - provider/API usage evidence.
  - first blocker or delivery result.

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-interface-repair-api-retest.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-interface-repair-api-retest.md`
  - `issue_memory/modifications.jsonl`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated project source files
  - production source code
  - local deterministic project templates/materializers
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no local project template fallback as proof.
  - no generated-run source patching.
  - no provider credential changes.
- Acceptance Checks:
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-interface-repair-api-20260509 --goal <voice assistant goal>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 12`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>`
  - inspect `<run_dir>\artifacts\source_generation_report.json`
  - inspect `<run_dir>\artifacts\provider_ledger_summary.json`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`

## Analysis / Find

- Prior evidence:
  - `voice-assistant-signature-retest-20260508` reached API source_generation but failed `generic_validation`.
  - signature drift and abstract stub evidence were then wired into validation and retry prompts.
- Test target:
  - whether a fresh API-authored bundle now converges or fails at a clearer first blocker.
- External research artifact: none.

## Integration Check

- upstream: source_generation interface repair loop hardening.
- current_module: CTCP orchestrator external run.
- downstream: generated project validation and final delivery gate.
- source_of_truth: run artifacts under external run_dir.
- fallback: record first blocker instead of manual generated-source repair.
- acceptance_test:
  - bounded new-run/advance/status.
  - report inspection.
  - metadata gates.
- forbidden_bypass:
  - no local templates.
  - no generated project patching.
- user_visible_effect: user can see whether CTCP itself, through API, can produce the requested project.

## DoD Mapping

- [x] DoD-1: Fresh external API run created.
- [x] DoD-2: Run advanced with bounded API usage.
- [x] DoD-3: Source generation and provider evidence inspected.
- [x] DoD-4: First blocker or delivery result recorded.
- [x] DoD-5: Metadata gates pass or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Run a fresh API-only generation after the interface repair.
- contrast:
  - Compare against the previous signature retest failure class.
- fix:
  - No code fix in this task; record concrete evidence for the next bounded repair if needed.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: orchestrator invokes API source_generation.
- accumulated: run artifacts capture source_generation and validation evidence.
- consumed: report converts first blocker into next repair guidance.

## Issue Memory Decision Evidence

- issue_memory_decision: required and recorded as `20260509_003` because the API retest confirmed a new upstream intent/spec collapse plus stale prompt leakage failure.

## Plan

1. Bind the API retest task.
2. Run preflight metadata/protection checks.
3. Create a fresh external run with the concrete voice-assistant goal.
4. Advance the run with bounded API usage.
5. Inspect source_generation and provider artifacts.
6. Record result, issue memory if needed, and close metadata.

## Acceptance

- [x] DoD written.
- [x] Code changes disabled for this test task.
- [x] API run completed or first blocker recorded.
- [x] Metadata closure checks pass.

## Results

- External run: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\voice-assistant-interface-repair-api-20260509`.
- `new-run`: PASS, rc=0, 0.602s.
- Initial `status`: running, blocked on `artifacts/analysis.md`.
- `advance --max-steps 12`: timed out after 1204.604s. Two residual `advance` processes for this run were stopped to avoid duplicate API spend.
- Final `status`: running, blocked on `artifacts/source_generation_report.json`; `source_generation_report.json` was not written.
- Provider/API evidence:
  - `provider_ledger_summary.json`: `critical_step_count=7`, `critical_api_step_count=7`, `fallback_count=0`, `all_critical_steps_api=true`.
  - `api_calls.jsonl`: `source_generation` count=7, model=`gpt-4.1`, status=`OK`.
- Generated partial project evidence:
  - Generated under `project_output/readme` with package `readme`, despite the user asking for a phone-to-PC voice assistant.
  - `output_contract_freeze.json` collapsed the request to `project_domain=generic_software_project`, `project_id=readme`, and a generic compatibility fallback intent.
  - Latest source_generation prompt still contained stale VN/GUI requirements such as story/scene/branch editor and `run_project_gui.py` compatibility language.
  - `py_compile` over generated Python files: PASS.
  - `scripts/run_project_web.py --help`: PASS.
  - `scripts/run_project_web.py --serve`: FAIL, unrecognized argument `--serve`.
  - `scripts/run_project_web.py --headless --goal test --project-name readme --out <out>`: FAIL, `AttributeError: 'dict' object has no attribute 'strip'`.
  - `python -m unittest discover -s tests -v`: FAIL, 4 tests run with 1 failure and 3 errors from service/test API drift.
- First blocker:
  - The API run did not produce a successful source_generation report or deliverable.
  - The first concrete repair target is upstream project intent/spec shaping and stale prompt leakage, not local templates or manual generated-source patching.
- Closure verify:
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`: PASS.
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`: PASS.
  - `.venv\Scripts\python.exe scripts\patch_check.py`: PASS.
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` with API-forcing env vars removed and `CTCP_SKIP_LITE_REPLAY=1`: PASS, 525 Python tests OK, 4 skipped.

## Notes / Decisions

- Default choice made: use the same voice-assistant goal for comparability with previous runs.
- Skill decision: skillized: yes, using `ctcp-orchestrate-loop` because this task drives `scripts/ctcp_orchestrate.py` state.
- persona_lab_impact: none.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
