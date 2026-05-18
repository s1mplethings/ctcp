# Task Archive: Live Provider Blind Small Project Matrix

## Queue Binding
- Queue Item: `ADHOC-20260518-live-provider-blind-matrix`
- Lane: Delivery Lane
- Status: completed

## Scope
- Add `live_provider_blind_candidate` support.
- Add a five-case blind small project matrix.
- Preserve ordinary `new-run/status/advance`.
- Do not add dedicated deterministic fast paths for blind cases.
- Preserve attribution, Review Pack evidence, validation, and deterministic fallback.

## Outcomes
- Blind cases:
  - `live_provider_unit_converter_cli`: fallback
  - `live_provider_file_renamer_cli`: repaired
  - `live_provider_markdown_table_formatter`: fallback
  - `live_provider_json_config_validator`: repaired
  - `live_provider_static_site_generator`: repaired
- `provider_request_count=5`
- `provider_project_candidate_count=5`
- `accepted_count=0`
- `repaired_count=3`
- `fallback_count=2`
- `unsupported_count=0`
- `failed_count=0`
- `repair_attempt_count=3`

## Verification
- Blind matrix benchmark: PASS.
- Existing full-candidate/live-provider/provider-assisted/full-stack/non-web/concrete/agent benchmarks: PASS.
- `unittest discover`: PASS `790` tests, `4` skipped.
- Final repo verification: recorded in `meta/reports/LAST.md`.
