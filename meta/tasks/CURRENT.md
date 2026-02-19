# Task - teamnet-dispatcher-provider-manual-outbox

## Context
- Add TeamNet dispatcher/provider automation layer on top of the existing orchestrator state machine.
- Keep resolver-first and external-run constraints unchanged.
- Implement only local pluggable providers without network/API calls:
  - `manual_outbox` provider for API roles.
  - `local_exec` provider only for local librarian auto-execution.
- Add lite regression coverage for dispatcher behavior.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local contract alignment)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Spec-first: update TeamNet/artifact docs for `dispatch_config` and outbox prompt contract.
2) Implement dispatcher core + providers (`manual_outbox`, `local_exec`) and orchestrator integration (`status`/`advance`).
3) Add prompt templates under `agents/prompts/` for Chair/Guardian/Cost/Patch/Fix/Research (+ librarian template compatibility).
4) Add 1-2 lite SimLab scenarios for dispatcher outbox and librarian local-exec behavior.
5) Run `python scripts/sync_doc_links.py --check` and `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
6) Update `meta/reports/LAST.md` with readlist/plan/verify/demo pointer.

## Notes / Decisions
- `find_result.json` remains the only resolver authority; `find_web` is candidate input only.
- Runs remain outside repo under `CTCP_RUNS_ROOT`; repo keeps only run pointers.
- No new dependencies.

## Results
- Added dispatcher/provider layer:
  - `scripts/ctcp_dispatch.py`
  - `tools/providers/manual_outbox.py`
  - `tools/providers/local_exec.py`
- Integrated dispatch into `scripts/ctcp_orchestrate.py` (`new-run/status/advance`) with:
  - auto-created `artifacts/dispatch_config.json`
  - `OUTBOX_PROMPT_CREATED` and `OUTBOX_PROMPT_FULFILLED` events
  - budget stop (`STOP_BUDGET_EXCEEDED`)
  - librarian local-exec path
- Added prompt templates under `agents/prompts/`.
- Added/updated lite scenarios:
  - `S12_lite_orchestrate_context_gate` (updated)
  - `S13_lite_dispatch_outbox_on_missing_review` (new)
  - `S14_lite_dispatch_local_exec_librarian` (new)
- Verification:
  - `python scripts/sync_doc_links.py --check` passed
  - `python simlab/run.py --suite lite` passed (`6/6`)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` passed
