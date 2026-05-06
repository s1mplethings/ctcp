# Task Archive - Generation Provenance Ledger

- Queue Item: `ADHOC-20260501-generation-provenance-ledger`
- Date: `2026-05-01`
- Status: `done`

## Scope

The task fixed the user-visible attribution gap where `provider_ledger.jsonl` could show `api_agent` for `source_generation`, while the final project files were actually written by CTCP local materializers.

## Completed DoD

- [x] `source_generation` reports distinguish remote provider execution from local file materialization.
- [x] Generated project files include auditable per-file provenance records consumed by `project_manifest`.
- [x] Regressions prove `source_generation` no longer implies API-authored final source files when local materializers write them.

## Key Changes

- Added shared provenance helpers in `tools/providers/project_generation_provenance.py`.
- Added provenance fields to `source_generation_report.json` and `project_manifest.json`.
- Added local librarian prompt evidence for `local_exec` context-pack generation.
- Added focused tests for generation provenance and local-exec librarian evidence.
- Aligned existing tests to current `librarian/context_pack -> local_exec` hard-lock behavior.

## Verification

- `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` passed.
- `python -m unittest discover -s tests -p "test_project_generation_provenance.py" -v` passed.
- `python -m unittest discover -s tests -p "test_local_exec_librarian_evidence.py" -v` passed.
- `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v` passed.
- `python -m unittest discover -s tests -p "test_mock_agent_pipeline.py" -v` passed.
- Triplet guard tests passed.
- `python simlab\run.py --suite lite --runs-root "$env:TEMP\ctcp_runs\ctcp\simlab_runs"` passed with `15` passed and `0` failed.
- `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` passed with exit `0`.
