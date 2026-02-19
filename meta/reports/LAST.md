# Demo Report — LAST

## Goal
- Implement Local Orchestrator artifact-driven progression with optional controlled web-find artifact gating, while keeping ADLC mainline unchanged and enforcing stricter repo hygiene gates.

## Readlist
- `ai_context/00_AI_CONTRACT.md`
  - Enforce task-first, verify entrypoint, and auditable report output.
- `README.md`
  - Core execution defaults and verify entrypoints.
- `BUILD.md`
  - Headless lite build assumptions.
- `PATCH_README.md`
  - Minimal patch + verify requirements.
- `TREE.md`
  - Repository structure reference.
- `docs/03_quality_gates.md`
  - Lite replay and workflow/contract/doc-index gate obligations.
- `ai_context/problem_registry.md`
  - Evidence-first verify discipline.
- `ai_context/decision_log.md`
  - No bypass entries needed.
- `docs/00_CORE.md`
  - Canonical protocol source (updated to v0.1 contract text).

## Plan
1) Write/update the 4 contract documents as the source of truth.
2) Refactor orchestrator into strict artifact-gated progression with review/signature gates.
3) Add optional `find_web` contract + offline validation and lite check scenario.
4) Tighten verify_repo anti-pollution gate for build/run outputs tracked or appearing in repo.
5) Run orchestrator checks + `scripts/verify_repo.ps1` and record evidence.

## Timeline / Trace pointer
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- External run folder: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260219-152020-orchestrate`
- Trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260219-152020-orchestrate\TRACE.md`

## Changes
- Contract docs (source of truth)
  - `docs/00_CORE.md` rewritten to `CTCP Core Contract (v0.1)`.
  - `docs/21_paths_and_locations.md` rewritten to `Paths and Locations (v0.1)`.
  - Added `docs/22_teamnet_adlc.md` (`TeamNet x ADLC Overview (v0.1)`).
  - Added `docs/30_artifact_contracts.md` (`Artifact Contracts (v0.1)`).
- Workflow/docs integration
  - `docs/02_workflow.md` updated with Local Orchestrator artifact-progression + find mode notes.
  - `README.md` updated with controlled optional web-find note while default remains offline.
  - `scripts/sync_doc_links.py` updated curated index list to include new docs and README index resynced.
- Artifact schemas
  - Updated `specs/ctcp_file_request_v1.json` to `needs[] + budget + reason` contract.
  - Updated `specs/ctcp_context_pack_v1.json` to `omitted[]` structured objects with reason enum.
  - Added/updated `specs/ctcp_find_web_v1.json` with `constraints(max_queries,max_pages,allow_domains)` and structured locator.
- Orchestrator implementation
  - Rewrote `scripts/ctcp_orchestrate.py` as strict artifact-driven state machine.
  - `new-run`: creates external run layout (`repo_ref.json`, `events.jsonl`, `artifacts/`, `reviews/`, `logs/`, `snapshot/`, `TRACE.md`) and writes `meta/run_pointers/LAST_RUN.txt`.
  - `status`: shows missing artifact/block reason and responsible role.
  - `advance`: gates on `guardrails -> analysis -> find_result -> (optional find_web) -> file_request -> context_pack -> PLAN_draft -> reviews APPROVE -> PLAN signed -> diff.patch -> apply -> verify`.
  - `resolver_plus_web` mode now blocks on missing/invalid `artifacts/find_web.json` with owner `Researcher`.
  - verify output switched to `artifacts/verify_report.json` with required fields.
- Gate/quality updates
  - Added `tools/checks/find_web_contract.py` (offline find_web schema checker).
  - Added `simlab/scenarios/S11_lite_find_web_contract.yaml` (lite contract check scenario).
  - Existing `simlab/run.py` empty-suite fail behavior remains active (`no scenarios` => exit 1).
- Repo hygiene gate hardening
  - `scripts/verify_repo.ps1` and `scripts/verify_repo.sh` now fail on:
    - tracked build outputs
    - tracked run outputs (`meta/runs`, `simlab/_runs*`)
    - unignored build/run outputs in repo
  - Why this gate is mandatory:
    - tracked build/run artifacts break repo cleanliness and make `verify_repo` non-reproducible across machines.
    - in-repo run outputs violate the external blackboard contract (`CTCP_RUNS_ROOT`) and pollute review diffs.
  - lite replay default runs are now external (`python simlab/run.py --suite lite`); in-repo fixture path only when `CTCP_WRITE_FIXTURES=1`.
- Pollution cleanup to satisfy new gate
  - Removed tracked historical run outputs from git index:
    - `meta/runs/**`
    - `simlab/_runs/**`

## Verify
- Syntax checks:
  - `python -m py_compile scripts/ctcp_orchestrate.py scripts/resolve_workflow.py simlab/run.py tools/checks/find_web_contract.py tools/run_paths.py`
  - Result: pass.
- Orchestrator creation:
  - `python scripts/ctcp_orchestrate.py new-run --goal "smoke"`
  - Result: pass; run created under external root and pointer updated.
- Orchestrator progression to librarian gate:
  - Prepared `artifacts/guardrails.md`, `artifacts/analysis.md`, `artifacts/file_request.json`, then ran:
  - `python scripts/ctcp_orchestrate.py advance --max-steps 8`
  - Result: blocked on `artifacts/context_pack.json` with owner `Local Librarian`.
- Optional web-find gate behavior (resolver_plus_web):
  - Switched guardrails to `find_mode: resolver_plus_web`, then ran:
  - `python scripts/ctcp_orchestrate.py advance --run-dir <last_run> --max-steps 4`
  - Result: blocked on `artifacts/find_web.json` with owner `Researcher`.
- Mandatory gate:
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1`
  - Exit: `0`
  - Key output:
    - anti-pollution gate passed
    - headless lite build + ctest passed
    - workflow/contract/doc-index checks passed
    - lite scenario replay passed with `passed: 3, failed: 0`
    - `[verify_repo] OK`

## Open questions (if any)
- None.

## Next steps
- Commit the full contract + orchestrator + gate patch as a single focused change set.
- Optionally add a negative lite scenario for invalid `find_web.json` to assert expected fail path explicitly.
