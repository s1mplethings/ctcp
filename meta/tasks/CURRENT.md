# Task - patch-first-editing-protocol

## Queue Binding
- Queue Item: `N/A (user-directed hotfix task)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- Integrate Aider-style patch-first editing into existing orchestrator/dispatcher flow.
- All repo modifications must be expressed as unified diff and pass strict gates before apply.

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: patch-first gate is enforceable and auditable in orchestrator flow
- [x] DoD-2: failure bundle always contains diff.patch and rejection evidence
- [x] DoD-3: unit + integration verification proves rejection/apply behavior

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local implementation)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first
   - update patch contract and orchestrator/dispatcher specs for patch-first gate
2) Implement patch-first module + CLI
   - add `tools/patch_first/*`
   - add `scripts/apply_patch_first.py`
3) Wire orchestrator apply path
   - replace direct `git apply` with patch-first safe apply
   - write structured rejection review and preserve candidate patch evidence
4) Verify and report
   - run targeted unit + simlab scenario + `scripts/verify_repo.ps1`
   - update `meta/reports/LAST.md`

## Notes / Decisions
- No new third-party dependency; Python stdlib only.
- Default policy limits: `max_files=5`, `max_added_lines=400`.

## Results
- Added patch-first module and CLI:
  - `tools/patch_first/core.py`
  - `tools/patch_first/__init__.py`
  - `scripts/apply_patch_first.py`
- Orchestrator apply path now uses patch-first gates and writes rejection evidence:
  - `scripts/ctcp_orchestrate.py`
  - `tools/providers/manual_outbox.py`
- Added patch retry prompt templates:
  - `agents/prompts/patchmaker_patch.md`
  - `agents/prompts/fixer_patch.md`
- Added unit/integration verification:
  - `tests/test_patch_first.py`
  - `simlab/scenarios/S17_lite_patch_first_reject.yaml`
  - `simlab/run.py` (ignore repo `runs/` in copy sandbox)
- Validation passed:
  - `python -m unittest discover -s tests -p "test_patch_first.py"`
  - `python simlab/run.py --suite lite --sandbox-mode copy`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## Follow-up (2026-02-21) - Minimal Live API Smoke
- Goal: test direct API path with minimal API usage.
- Scope: no repo code change; runtime env + one `/responses` request only.
- Commands:
  - `python tools/checks/suite_gate.py --json` (after setting `OPENAI_API_KEY` and `CTCP_ALLOW_NETWORK=true`)
  - one direct call via `scripts/externals/openai_responses_client.py` import (`model=gpt-4.1-mini`, prompt=`Reply with exactly: OK`)
- Outcome:
  - suite gate `ready=true`
  - API call success with text `OK`

## Follow-up (2026-02-21) - Diffpatch Success-Rate Benchmark
- Goal: benchmark patch generation success rate and identify better prompt structure.
- Scope:
  - API-only evaluation (small sample) on temporary git repos.
  - Measure `parse -> policy -> git apply --check -> apply` pass rate via `tools.patch_first.apply_patch_safely`.
  - No business-code modifications.
- Planned sample size:
  - 3 prompt structures × 3 trials (total 9 API calls, default minimal viable sample).
- Outputs:
  - `meta/externals/20260221-diffpatch-prompt-benchmark.md`
  - `meta/reports/LAST.md` addendum with command/result summary.
- Completed:
  - Round 1 (9 calls): baseline prompts failed due parse/git-check format details.
  - Round 2 (9 calls): improved prompts reached 100% apply success (9/9).
  - Selected prompt structure: `skeleton_v2` (short contract + explicit diff shape + trailing newline).
