# Demo Report — LAST

## Goal
- Keep ADLC mainline unchanged while extending `find` protocol to support controlled optional web artifacts (`find_local` mandatory + `find_web` optional), with Local Orchestrator artifact-driven gating.

## Readlist
- `ai_context/00_AI_CONTRACT.md`
  - Task-first + verify-repo-only acceptance + auditable LAST report.
- `README.md`
  - Headless default and no hard web dependency in core flow.
- `BUILD.md`
  - Headless lite build path assumptions for verify gate.
- `PATCH_README.md`
  - Minimal patch + `verify_repo` pass is required.
- `TREE.md`
  - Existing docs/spec/meta layout baseline.
- `docs/03_quality_gates.md`
  - Lite replay is mandatory gate coverage.
- `ai_context/problem_registry.md`
  - Evidence-first verification requirement.
- `ai_context/decision_log.md`
  - No bypass decisions used.
- `docs/00_CORE.md`
  - Canonical ADLC chain and precedence rule.
- `docs/02_workflow.md`
  - Workflow semantics and orchestration behavior baseline.
- `scripts/ctcp_orchestrate.py`
  - Existing artifact-driven runner implementation to extend.
- `simlab/run.py`
  - Lite scenario replay implementation.

## Plan
1) Doc/spec-first: update `docs/00_CORE.md`, `docs/02_workflow.md`, `README.md`; add `specs/ctcp_find_web_v1.json`.
2) Extend orchestrator protocol for `find_mode` and `find_web.json` gating without any network calls.
3) Update guardrails template fields (`find_mode`, `web_find_policy`).
4) Add lite-level contract check scenario for `resolver_plus_web` web-find artifact completeness.
5) Run orchestrator smoke checks and `scripts/verify_repo.ps1`; record outputs.

## Timeline / Trace pointer
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- External run folder: `C:\Users\sunom\.ctcp\runs\ctcp\20260219-144245-orchestrate`
- Trace: `C:\Users\sunom\.ctcp\runs\ctcp\20260219-144245-orchestrate\TRACE.md`

## Changes
- `docs/00_CORE.md`
  - Updated section 1.2 to dual-channel find protocol:
    - default `resolver_only`
    - optional `resolver_plus_web` under guardrails
    - `find_web.json` is input only; final decision remains `find_result.json`
  - Updated role section to define Local Orchestrator as the single run driver.
  - Extended 5.3 find section with `find_local` + `find_web` gate semantics.
- `docs/02_workflow.md`
  - Added Local Orchestrator artifact-progression rules and mode gates (`resolver_only` vs `resolver_plus_web`).
- `README.md`
  - Added controlled optional web-find note while keeping default offline/headless behavior.
- `specs/ctcp_find_web_v1.json`
  - Added minimal web-find artifact contract: `schema_version`, `constraints`, `results[]` fields.
- `docs/13_contracts_index.md`
  - Added `ctcp_find_web_v1.json` entry.
- `scripts/ctcp_orchestrate.py`
  - Added `new-run` args: `--find-mode`, `--web-allow-domain`, `--web-max-queries`, `--web-max-results`.
  - `RUN.json` now records `find_mode` and `web_find_policy`.
  - Guardrails template now includes `find_mode` + `web_find_policy`.
  - Added `find_web.json` contract validator and gating:
    - `resolver_only`: requires `find_result.json`
    - `resolver_plus_web`: requires both `find_result.json` and valid `find_web.json`; otherwise blocked with owner `Researcher`.
- `tools/checks/find_web_contract.py`
  - Added offline validator for `ctcp-find-web-v1` artifact completeness.
- `simlab/scenarios/S11_lite_find_web_contract.yaml`
  - Added lite scenario that writes `find_web.json` and validates contract in `resolver_plus_web` mode.

## Verify
- Syntax checks:
  - `python -m py_compile scripts/ctcp_orchestrate.py simlab/run.py tools/checks/find_web_contract.py`
  - Result: pass.
- New run in `resolver_plus_web` mode:
  - `python scripts/ctcp_orchestrate.py new-run --goal "web-smoke" --find-mode resolver_plus_web`
  - Result: pass; run created and pointer updated.
- Mode gate behavior:
  - `python scripts/ctcp_orchestrate.py advance`
  - Result: blocked as expected: `missing artifacts/find_web.json (owner=Researcher)`.
  - `python scripts/ctcp_orchestrate.py status`
  - Result: `next_missing=artifacts/find_web.json`, `owner=Researcher`.
- Mandatory gate:
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1`
  - Exit: `0`
  - Key output: anti-pollution gate pass, ctest pass, workflow/contract/doc-index pass, lite replay pass (`passed: 3, failed: 0`), `[verify_repo] OK`.

## Open questions (if any)
- None.

## Next steps
- Commit this protocol extension as one focused patch (docs/specs/orchestrator/lite check).
- If needed, add a second lite negative scenario (invalid `find_web.json` should fail contract check).
