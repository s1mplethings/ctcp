# Report Archive - Live Provider-Assisted Smoke Path

## Summary

Phase 17 added `live_provider_assisted` mode for ordinary concrete project generation. The live provider is called only for bounded helper/documentation/frontend-helper fragments, while deterministic materializers retain ownership of core app structure, persistence, generated tests, and runtime validation.

## Verification

- `tests/live_provider_benchmark/run_live_provider_benchmark.py` -> PASS `3/3`, `provider_request_count=3`, `provider_fragment_count=3`, `fallbacks=0`.
- Live provider unit tests -> PASS.
- Existing provider-assisted, non-web, full-stack, concrete matrix, concrete issue tracker, and agent benchmarks -> PASS.
- `python -m unittest discover tests -v` -> PASS `762` tests, `4` skipped.
- `scripts/verify_repo.ps1 -Profile code` -> PASS.

## Key Paths

- `tools/providers/live_provider_adapter.py`
- `tools/providers/project_generation_provider_assisted.py`
- `tests/live_provider_benchmark/benchmark_report.md`
- `tests/live_provider_benchmark/generated/live_provider_summary.json`
- `meta/reports/REVIEW_PACK.md`
