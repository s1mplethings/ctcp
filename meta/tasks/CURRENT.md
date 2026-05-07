# Task - Agent Interaction Source Repair

## Queue Binding

- Queue Item: `ADHOC-20260507-agent-interaction-source-repair`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: a fresh phone-to-PC voice assistant generation run used `api_agent` for source_generation, but the delivered project still failed when tested as a real user project.
- Lane: Delivery Lane.
- Scope boundary: strengthen the source_generation retry interaction loop so QA/validator failures become concrete repair instructions for the next API source-generation attempt.

## Task Truth Source

- task_purpose:
  - Generated project failures must not remain as opaque validation JSON; they must be translated into actionable Builder/Integration QA/Product QA/Delivery QA repair items consumed by the next source_generation prompt.
  - The live failure classes to cover are bare sibling imports, package `__init__` re-export drift, constructor/API signature mismatches, README section mismatch, and missing runnable web/mobile endpoint evidence.
  - Provider-authored source remains required; no local deterministic project template or generated-project patch fallback is allowed.
- allowed_behavior_change:
  - Source-generation prompt requirements may define a stricter multi-role repair protocol.
  - Previous-failure feedback may classify runtime probe errors into actionable inter-agent handoff items.
- forbidden_goal_shift:
  - Do not install dependencies to mask broken generated projects.
  - Do not weaken generic/readme/ux/product validation.
  - Do not edit generated run output as the fix.
  - Do not change Telegram/support runtime behavior.
- in_scope_modules:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_agent_templates.py`
  - `issue_memory/modifications.jsonl`
  - repo task/report metadata
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - Telegram/support bot files
  - provider credentials and endpoint config
  - external run directories
- completion_evidence:
  - focused source-generation prompt tests pass.
  - source-generation artifact tests still pass.
  - workflow/code-health/canonical verify pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_agent_templates.py`
  - `issue_memory/modifications.jsonl`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260507-agent-interaction-source-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260507-agent-interaction-source-repair.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories
  - local API/proxy secrets
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no validation relaxation
  - no local template fallback
  - no generated-run source patching as proof
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_api_agent_templates.py`
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v`
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Live failure evidence: `voice-assistant-phone-pc-smoke-20260507-rerun` produced provider-authored files with `fallback_count=0`, then failed concrete project tests.
- First failure chain:
  - `scripts/run_project_web.py --help` failed before argparse because package import reached `src/readme/app.py`.
  - `app.py` used bare sibling import `import service`, causing `ModuleNotFoundError: No module named 'service'` under src-layout package execution.
  - After PYTHONPATH workaround, `VoiceAssistantService()` failed because `CommandWhitelist.__init__()` required `commands`.
  - HTTP endpoint tests timed out because the server thread crashed before serving `/status` or `/`.
- Current gap:
  - The prompt already asks for runnable output and previous failure feedback, but it does not frame the validator as a QA agent handing a mandatory repair contract back to the Builder.
  - Previous failure text does not explicitly classify bare sibling import failures, constructor signature mismatches, or web/mobile endpoint obligations.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: API source-generation prompt renderer via `ctcp_adapters.ctcp_artifact_normalizers._render_prompt()`.
- current_module: `ctcp_adapters/source_generation_prompt.py`.
- downstream: chunked API source generation, provider-authored file materialization, generic/readme/ux validation, and next retry prompt.
- source_of_truth: `artifacts/source_generation_report.json` plus live concrete generated-project test evidence.
- fallback: if focused tests fail, keep changes to prompt text and previous-failure classification only.
- acceptance_test:
  - source-generation prompt tests
  - source-generation artifact tests
  - canonical verify code profile
- forbidden_bypass:
  - no validation relaxation
  - no local template fallback
  - no dependency installation workaround
- user_visible_effect: future retries should give the API agent a clearer QA handoff and reduce repeated broken import/signature/web endpoint outputs.

## DoD Mapping

- [x] DoD-1: Prompt defines explicit Builder/Integration QA/Product QA/Delivery QA interaction duties.
- [x] DoD-2: Previous failure feedback converts the live failure classes into actionable repair items.
- [x] DoD-3: Focused tests and canonical verify pass or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Concrete generated-project tests failed even though provider source files existed and syntax compiled.
  - Startup/import path failed at `ModuleNotFoundError: No module named 'service'`.
  - Direct service construction failed at `CommandWhitelist.__init__()` missing `commands`.
  - Web/mobile endpoint probe failed because `/status` and `/` never became reachable.
- contrast:
  - The previous dependency-focused hardening improved the run from Flask dependency failure to standard-library HTTP generation, so the next failure class is cross-file integration and agent handoff quality.
  - Existing previous-failure feedback carried raw stderr but did not turn it into a mandatory Builder/Integration QA/Product QA/Delivery QA repair contract.
- fix:
  - Added source-generation handoff duties for Builder, Integration QA, Product QA, and Delivery QA.
  - Added targeted runtime-probe repair hints for bare sibling imports, missing re-exports, constructor signature mismatches, and server reachability failures.
  - Added focused tests that replay the live failure classes in the next source_generation prompt.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: `ctcp_adapters.ctcp_artifact_normalizers._render_prompt()` calls the source-generation requirements renderer for `chair/source_generation`.
- accumulated: `issue_memory/modifications.jsonl` records the recurring generated-project integration failure.
- consumed: focused prompt tests assert that the inter-agent handoff and exact live failure repair hints appear in the prompt consumed by the API source-generation path.

## Plan

1. Bind task and allowed write scope.
2. Strengthen source-generation prompt with a concrete inter-agent repair protocol.
3. Add previous-failure classifiers for bare sibling imports, constructor/API signature mismatches, package export drift, and web/mobile endpoint failures.
4. Add regression assertions for the live failure classes.
5. Run focused checks and canonical verify.
6. Archive task/report and record worktree state.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed.
- [x] Prompt/runtime repair guidance updated.
- [x] Focused tests pass.
- [x] Code-health check passes.
- [x] Canonical verify pass or first failure recorded.
- [x] Demo report updated: `meta/reports/LAST.md`.

## Notes / Decisions

- Default choice made: improve the inter-agent feedback contract inside the source-generation prompt path because live evidence shows the API did generate code but did not consume failures with enough specificity.
- Alternatives considered: adding a local generated-project auto-repairer was rejected because it would hide whether `api_agent` actually produced the working project.
- Any contract exception reference: none.
- Issue memory decision: required because this is a recurring user-visible generated-project failure.
- Skill decision: skillized: no, because this is a local source-generation repair loop enhancement; it can become a skill only after the pattern stabilizes across several domains.
- persona_lab_impact: none.

## Results

- Files changed:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_agent_templates.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260507-agent-interaction-source-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260507-agent-interaction-source-repair.md`
- Verification summary:
  - focused source-generation prompt tests passed.
  - focused source-generation artifact tests passed.
  - workflow/module/patch/code-health checks passed.
  - canonical verify passed with profile `code`, ownership `task-owned`, lite replay `15 passed / 0 failed`, Python tests `517 OK / 4 skipped`.
- Queue status update: `done`.

## Closure

- closed_report: `meta/reports/archive/20260507-agent-interaction-source-repair.md`
- canonical_verify: passed on 2026-05-07 with `CTCP_FORCE_PROVIDER` cleared and `CTCP_RUNS_ROOT` set to `%TEMP%\ctcp_runs`.
