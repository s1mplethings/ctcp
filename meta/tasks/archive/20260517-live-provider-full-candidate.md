# Task Archive - Live Provider Full Small Project Candidate

## Queue Binding

- Queue Item: `ADHOC-20260517-live-provider-full-candidate`
- Lane: Delivery Lane
- Date Closed: 2026-05-17

## Scope

Add `live_provider_full_candidate` ordinary concrete generation mode. The mode keeps `new-run/status/advance`, accepts a complete small provider project candidate only after deterministic validation, and records candidate/fallback attribution.

## Changes

- Added `tools/providers/project_generation_live_full_candidate.py`.
- Wired full-candidate mode through provider-assisted mode detection, fast-path registry/defaults/provenance, materialization, source generation report, attribution, and API agent source-generation mode.
- Added `tests/live_provider_full_candidate_benchmark/`.
- Added focused tests: generation, attribution, validation, fallback, safety, and review pack.
- Updated README, `docs/project_generation.md`, and `docs/concrete_project_pipeline.md`.
- Stabilized concrete matrix server readiness polling without weakening endpoint/persistence validation.

## Evidence

- Live full-candidate benchmark: PASS `3/3`.
- Text stats CLI: PASS.
- Password policy package: PASS.
- Invalid provider candidate fallback: PASS.
- Existing live provider benchmark: PASS `3/3`.
- Provider-assisted benchmark: PASS `3/3`.
- Non-web matrix: PASS `4/4`.
- Full-stack benchmark: PASS `2/2`.
- Concrete matrix: PASS `3/3`.
- Concrete issue tracker: PASS.
- Agent planner/runtime/factory benchmarks: PASS.
- Unittest discover: PASS `777` tests, `4` skipped.
- Repo verify: PASS.

## Artifacts

- `tests/live_provider_full_candidate_benchmark/benchmark_report.md`
- `tests/live_provider_full_candidate_benchmark/generated/live_provider_full_candidate_summary.json`
- `meta/reports/REVIEW_PACK.md`

