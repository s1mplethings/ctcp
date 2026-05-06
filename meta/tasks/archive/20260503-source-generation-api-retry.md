# Task Archive - Source Generation API Retry

- Date: `2026-05-03`
- Queue Item: `ADHOC-20260503-source-generation-api-retry`
- Lane: Delivery Lane
- Status: done

## Scope

Retry transient API transport failures for `chair/source_generation` without enabling local fallback.

## Changes

- Added source_generation retry policy to `llm_core/providers/api_provider.py`.
- Added HTTP 504 / gateway timeout / Cloudflare retry markers to transient classification.
- Added focused regression in `tests/test_api_agent_templates.py`.

## Verification

- Focused py_compile, retry regression, workflow checks, and current-task code health passed.
- Canonical verify remains blocked by unrelated out-of-scope dirty lane files.
