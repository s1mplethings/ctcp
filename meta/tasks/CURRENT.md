# Task — find-dual-channel-and-orchestrator-gating

## Context
- Need to keep ADLC mainline unchanged while extending find semantics to support controlled optional web research artifacts.
- Local agent role must be Local Orchestrator (single driver) with artifact-existence state transitions.
- Add protocol for `find_local` (required resolver) + `find_web` (optional researcher artifact), without implementing real networking.
- Add lite-level gate/check for `resolver_plus_web` mode artifact completeness.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local design/implementation)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Doc/spec-first: update `docs/00_CORE.md`, `docs/02_workflow.md`, `README.md`, and add `specs/ctcp_find_web_v1.json`.
2) Update orchestrator protocol/gating for `find_mode` (`resolver_only` vs `resolver_plus_web`) and `find_web.json` blocking/validation.
3) Update guardrails template fields (`find_mode`, `web_find_policy`) and run metadata.
4) Add lite scenario/check for `resolver_plus_web` find-web artifact completeness (offline file check only).
5) Run verify (`scripts/verify_repo.ps1`) and refresh `meta/reports/LAST.md`.

## Notes / Decisions
- No real web search implementation in repo; web channel is external-agent artifact input only.
- No new dependencies; Python stdlib only.
- Keep runs default externalized via `tools/run_paths.py` and pointer in `meta/run_pointers/LAST_RUN.txt`.
- Keep GUI path untouched; default remains headless/lite.

## Results
- Updated protocol docs to define Local Orchestrator as single driver and `find` dual-channel mode (`resolver_only` / `resolver_plus_web`).
- Added `specs/ctcp_find_web_v1.json` and linked it in contracts index.
- Updated orchestrator run metadata + guardrails template to include `find_mode` and `web_find_policy`.
- Added orchestrator gate behavior: in `resolver_plus_web`, block on missing/invalid `artifacts/find_web.json` (owner=Researcher).
- Added lite contract check artifacts: `tools/checks/find_web_contract.py` and `simlab/scenarios/S11_lite_find_web_contract.yaml`.
- Verified `resolver_plus_web` block behavior and passed `scripts/verify_repo.ps1` in LITE mode.
