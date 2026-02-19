# Task — local-orchestrator-dual-find-protocol

## Context
- Need to align repository contracts to a single authority set: `docs/00_CORE.md`, `docs/21_paths_and_locations.md`, `docs/22_teamnet_adlc.md`, and `docs/30_artifact_contracts.md`.
- Need Local Orchestrator to be artifact-driven (missing artifact => blocked) while keeping ADLC mainline unchanged.
- Need optional web-find channel (`resolver_plus_web`) without implementing any real network search in repo code.
- Need verify gates to fail on tracked/in-repo build/run pollution and keep lite scenario gate real.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local contract + implementation task)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Replace/update the 4 contract docs as the primary source of truth.
2) Refactor `scripts/ctcp_orchestrate.py` to strict artifact-gated progression and review/signature gates.
3) Add optional `find_web` artifact contract + offline validator + lite scenario check.
4) Tighten verify_repo anti-pollution rules for tracked/in-repo build/run outputs.
5) Run orchestrator smoke checks and `scripts/verify_repo.ps1`, then record report.

## Notes / Decisions
- No GUI changes.
- No new dependencies; stdlib only.
- No real web search implementation: web-find remains external artifact input only.
- Keep decision authority in Chair artifacts (`PLAN_draft.md` / signed `PLAN.md` + review adjudication).

## Results
- Updated contract docs and path/team/artifact rules to v0.1 text.
- Implemented Local Orchestrator as artifact gate driver (no plan/review content generation).
- Added `ctcp_find_web_v1` schema and offline validator.
- Added lite scenario to validate `find_web.json` fields in `resolver_plus_web` mode.
- Updated verify gate to fail on tracked/unignored build and run outputs inside repo.
- Removed tracked historical run outputs from `meta/runs` and `simlab/_runs` to satisfy new gate.
- `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1` passed.
