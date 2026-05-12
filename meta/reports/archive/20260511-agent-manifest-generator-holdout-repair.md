# Agent Manifest Generator Holdout Repair

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `PATCH_README.md`
- `meta/tasks/CURRENT.md`
- `tools/agent_manifest_generator.py`
- `tests/test_agent_manifest_generator.py`
- `tests/agent_factory_benchmark/benchmark_report.md`
- `tests/agent_factory_benchmark/holdout_validators/*.py`
- `tests/agent_factory_benchmark/holdout_fixtures/*.json`

## Plan
1. Bind a generator repair task with fixtures and validators protected.
2. Add negative-context handling for charge and launch/release ambiguity.
3. Add minimality, regulated-domain safety profiles, and action-risk policy to the generator.
4. Extend generator unit tests for holdout regressions.
5. Run benchmark, focused gates, and canonical verify.

## Changes
- Modified `tools/agent_manifest_generator.py`.
- Extended `tests/test_agent_manifest_generator.py` from 12 to 23 tests.
- Regenerated benchmark outputs and `tests/agent_factory_benchmark/benchmark_report.md`.
- Added issue-memory entry `ai_context/problem_registry.md` Example 32.
- Did not modify Phase 1 fixtures, Phase 2 fixtures, Phase 2.5 holdout fixtures, or any benchmark validator.

## Verify
- PASS: `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` returned 0 with Phase 1 `6/6`, Phase 2 `8/8`, Holdout `10 pass / 0 fail / 0 warning / 0 unsupported`.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_generator -v` returned 0, 23 tests OK.
- PASS: `.venv\Scripts\python.exe -m py_compile tools\agent_manifest_generator.py scripts\generate_agent_manifest.py tests\agent_factory_benchmark\run_benchmark.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: triplet runtime wiring command evidence ran during canonical verify; `test_runtime_wiring_contract.py` ran 25 tests OK.
- PASS: triplet issue memory command evidence ran during canonical verify; `test_issue_memory_accumulation_contract.py` ran 3 tests OK.
- PASS: triplet skill consumption command evidence ran during canonical verify; `test_skill_consumption_contract.py` ran 3 tests OK.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. Python unit tests ran 573 tests OK, skipped 4.

## Questions
- None.

## Demo
- Benchmark report: `tests/agent_factory_benchmark/benchmark_report.md`.
- Phase 1 result: 6 passed, 0 failed, 0 unsupported.
- Phase 2 result: 8 passed, 0 failed, 0 warnings, 0 unsupported.
- Holdout before: 0 passed, 10 failed, 8 warnings, 0 unsupported.
- Holdout after: 10 passed, 0 failed, 0 warnings, 0 unsupported.
- H9 fixed: battery charging station `charge` no longer triggers billing/payment/refund.
- H10 fixed: product launch coordination no longer triggers incident/rollback/devops.

## Check/Contrast/Fix Loop Evidence
- check: initial benchmark confirmed Phase 2.5 failures; first repair reached 9/10 with one H10 failure.
- contrast: H10 failure was caused by broad release-notes detection and low-risk tool names containing `launch`.
- fix: tightened release-notes detection and renamed low-risk launch tools while keeping publish approval high risk.
- re-check: benchmark reached Phase 2.5 10/10 with 0 warnings and canonical verify passed.

## Completion Criteria Evidence
- completion criteria evidence: connected + accumulated + consumed.
- connected: benchmark calls the real `scripts/generate_agent_manifest.py` entrypoint.
- accumulated: generated outputs and summaries were regenerated under benchmark output directories.
- consumed: structural, semantic, and holdout validators all passed without modification.

## Issue Memory Decision Evidence
- issue memory decision evidence: added `ai_context/problem_registry.md` Example 32.
- reason: this was a route/domain misfire class now covered by benchmark and unit regressions.

## Skill Decision
- skill used: `ctcp-workflow`.
- reason: CTCP queue binding, scoped implementation, gate execution, and auditable reporting are required.
- skillized: no, because this repair is local to the agent manifest generator and benchmark loop.
