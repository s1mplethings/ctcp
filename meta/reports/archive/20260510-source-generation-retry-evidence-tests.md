# Report Archive - Source Generation Retry Evidence Tests

## Readlist

- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_source_generation_prompt_leakage.py`
- `tests/test_api_agent_templates.py`
- `tools/providers/mock_agent.py`

## Plan

1. Add live-API-shaped retry prompt regression.
2. Strengthen retry evidence rendering.
3. Run focused tests and gates.

## Changes

- Retry prompt now includes export probe `rc/status`, export exit-0 guidance, and single replacement batch guidance.
- Regression test covers export/signature/interface/visual evidence blockers from the live API run.
- Mock-agent content generator was split to satisfy code-health.

## Verify

- FIRST FAILURE: focused prompt test failed before renderer changes.
- PASS: focused prompt tests returned 0, 3 tests OK.
- PASS: api-agent templates returned 0, 22 tests OK.
- PASS: mock-agent pipeline tests returned 0, 5 tests OK.
- FIRST FAILURE: code-health failed on `mock_agent.py` long-function growth.
- PASS: code-health passed after helper split.
- PASS: module protection and patch check returned 0.
- PASS: triplet runtime wiring, issue memory, and skill consumption regressions returned 0.
- PASS: `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0 with `CTCP_RUNS_ROOT=D:\.c_projects\adc\ctcp_runs`; canonical verify included lite CMake/ctest, workflow, module protection, prompt contract, plan, patch, behavior catalog, contract, doc index, code-health, triplet guard, lite replay, and 533 Python tests OK with 4 skipped.

## Questions

- None.

## Demo

- Next API retry prompt receives concrete evidence for export `rc=1`, missing `out_dir`, signature metadata drift, and missing visual evidence.
