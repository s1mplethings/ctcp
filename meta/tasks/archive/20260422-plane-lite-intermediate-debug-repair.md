# Plane-lite Intermediate Debug Repair

## Scope
- Fix Plane-lite/Focalboard-lite benchmark debug failures in spec freeze, acceptance evidence, delivery pass gate, evidence bundle, and review provider error handling.

## Write Scope
- `contracts/project_domain_matrix.json`
- `contracts/project_capability_bundles.json`
- `tools/providers/project_generation_*`
- `scripts/ctcp_dispatch.py`
- `scripts/ctcp_orchestrate.py`
- `llm_core/providers/api_provider.py`
- `tests/test_plane_lite_benchmark_regression.py`
- `meta/reports/*`

## Acceptance
- Plane-lite freezes to task/project-management domain, not generic/web_service.
- Dispatch writes request/result/acceptance triplets.
- Delivery completion failure blocks run pass.
- Evidence zip includes intermediate chain.
- Review provider errors do not become OK reviews.

## Verify
- See `meta/reports/LAST.md`.
