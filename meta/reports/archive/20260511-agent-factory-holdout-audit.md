# Agent Factory Holdout Generalization Audit Report

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `tests/agent_factory_benchmark/run_benchmark.py`
- `tests/agent_factory_benchmark/benchmark_report.md`

## Plan
1. Freeze generator, CLI, schema, existing fixtures, and existing validators.
2. Add holdout fixtures H1-H10.
3. Add holdout validators for domain precision, regulated safety, minimality, action risk, and similarity.
4. Extend the runner/report with Phase 2.5.
5. Run focused gates and canonical verify.

## Changes
- Added ten holdout fixtures.
- Added five holdout validators.
- Extended runner/report with Phase 2.5 Holdout Generalization Audit.
- Generated holdout outputs and `holdout_summary.json`.
- Generator, CLI, schema, existing fixtures, and existing validators were not edited.

## Verify
- PASS: `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py` returned 0 with Phase 1 `6/6`, Phase 2 `8/8`, Holdout `0 pass / 10 fail / 8 warning / 0 unsupported`.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_agent_manifest_generator -v` returned 0, 12 tests OK.
- PASS: `.venv\Scripts\python.exe -m py_compile tests\agent_factory_benchmark\run_benchmark.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. Python unit tests ran 562 tests OK, skipped 4.

## Questions
- None.

## Demo
- Benchmark report: `tests/agent_factory_benchmark/benchmark_report.md`.
- Holdout generated outputs: `tests/agent_factory_benchmark/holdout_generated/`.
- Phase 1: 6 passed, 0 failed, 0 unsupported.
- Phase 2: 8 passed, 0 failed, 0 warnings, 0 unsupported.
- Phase 2.5: 0 passed, 10 failed, 8 warnings, 0 unsupported.

## First Failure And Repair
- first failure point evidence: holdout returned 10 failed cases and 8 warnings.
- repair: no generator repair was made because generator was frozen.
- minimal fix strategy: use holdout failures as next implementation targets.

## Check/Contrast/Fix Loop Evidence
- check: holdout benchmark generated JSON for all ten fixtures.
- contrast: Phase 1/2 stayed green while holdout exposed generalization gaps.
- fix: no generator fix by design; report findings only.
- re-check: focused gates and canonical verify passed.

## Completion Criteria Evidence
- completion criteria evidence: connected + accumulated + consumed.
- connected: holdout fixtures call the frozen real generator.
- accumulated: holdout outputs and summary are persisted.
- consumed: holdout validators feed the benchmark report.

## Issue Memory Decision Evidence
- issue memory decision evidence: no new issue-memory entry.
- reason: audit-only task that records failures without repairing runtime behavior.

## Skill Decision
- skill used: `ctcp-workflow`.
- reason: CTCP queue binding, scoped implementation, gate execution, and auditable reporting were required.
- skillized: no, because this holdout benchmark is repo-specific QA infrastructure.
