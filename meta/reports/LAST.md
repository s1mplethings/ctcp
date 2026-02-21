# Demo Report - LAST

## Goal
- Integrate patch-first editing protocol into orchestrator/dispatcher flow:
  - patch-only repo edits (unified diff)
  - strict three-gate apply path
  - rejection evidence + fixer retry loop
  - failure bundle keeps candidate patch and reasons

## Readlist
- `ai_context/00_AI_CONTRACT.md` (hard process contract, question policy, report format)
- `README.md` (verify/doc index expectations and gate entrypoints)
- `BUILD.md` (headless build contract)
- `PATCH_README.md` (patch delivery baseline)
- `TREE.md` (repo structure orientation)
- `docs/03_quality_gates.md` (verify gate expectations)
- `ai_context/problem_registry.md` (known failure modes)
- `ai_context/decision_log.md` (no bypass needed for this change)
- `docs/PATCH_CONTRACT.md` (updated patch-first contract target)
- `docs/30_artifact_contracts.md` (artifact evidence contracts)
- `specs/modules/orchestrator.md` (orchestrator scope/gates)
- `specs/modules/dispatcher_providers.md` (dispatch mapping and outbox behavior)
- `scripts/ctcp_orchestrate.py` (apply + bundle + dispatch integration point)
- `scripts/ctcp_dispatch.py` (blocked->fixer request mapping)
- `tools/providers/manual_outbox.py` (outbox prompt hard rules)
- `scripts/verify_repo.ps1` / `simlab/run.py` (verification entrypoints)

## Plan
1. Docs/Spec first:
   - update patch/artifact/module contracts to define patch-first gates and retry behavior
2. Code:
   - add patch-first module + CLI
   - replace orchestrator direct `git apply` with safe apply gate
   - add rejection review/outbox/bundle evidence path
3. Verify:
   - run new unit tests
   - run simlab lite suite with new patch-first rejection scenario
   - run `scripts/verify_repo.ps1`
4. Report:
   - update task and LAST demo report

## Timeline / Trace Pointer
- Run pointer file: `meta/run_pointers/LAST_RUN.txt`
- SimLab lite run (manual):
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260221-090328`
- verify_repo lite replay run:
  - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260221-090526`

## Changes
- Added:
  - `tools/patch_first/__init__.py`
  - `tools/patch_first/core.py`
  - `scripts/apply_patch_first.py`
  - `tests/test_patch_first.py`
  - `simlab/scenarios/S17_lite_patch_first_reject.yaml`
  - `agents/prompts/patchmaker_patch.md`
  - `agents/prompts/fixer_patch.md`
- Updated:
  - `scripts/ctcp_orchestrate.py`
    - apply path now uses patch-first gate (`path normalize -> policy -> git apply --check -> apply`)
    - patch rejection writes `reviews/review_patch.md` + `artifacts/patch_rejection.json`
    - patch rejection emits verify fail evidence and bundles candidate patch/reason
    - fixer outbox fallback enforces unified diff output
  - `tools/providers/manual_outbox.py`
    - outbox hard rule now enforces unified diff-only output for `artifacts/diff.patch`
  - `simlab/run.py`
    - copy sandbox now ignores repo `runs/` to prevent recursive run-artifact copy pollution
  - `docs/PATCH_CONTRACT.md`
  - `docs/30_artifact_contracts.md`
  - `specs/modules/orchestrator.md`
  - `specs/modules/dispatcher_providers.md`
  - `meta/tasks/CURRENT.md`

## Verify
- `python (scripted) -> git worktree add --detach <tmp> HEAD && git -C <tmp> apply --check _tmp_patch_first_output.diff`
  - exit `0` (`check_rc 0`)
- `python -m unittest discover -s tests -p "test_patch_first.py"`
  - exit `0`
  - `Ran 6 tests ... OK`
- `python simlab/run.py --suite lite --sandbox-mode copy`
  - exit `0`
  - summary: `passed=9 failed=0` (includes `S17_lite_patch_first_reject`)
- `python -m unittest discover -s tests -p "test_*.py"`
  - exit `0`
  - `Ran 32 tests ... OK`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - exit `0`
  - build/ctest/workflow/contract/doc-index/lite-simlab/python-tests all passed
  - lite replay summary: `passed=9 failed=0`

## Open Questions
- None.

## Next Steps
- None.

---

## Addendum (2026-02-21) - Minimal Live API Smoke

### Goal
- Run direct real-API smoke test with minimal API usage.

### Plan
1. Open live suite gate preconditions.
2. Perform exactly one `/responses` API call.
3. Record concise outcome.

### Verify
- `python tools/checks/suite_gate.py --json` (with `OPENAI_API_KEY` and `CTCP_ALLOW_NETWORK=true`)
  - exit `0`
  - `ready=true`, `status=pass`
- `python -` inline call using `scripts/externals/openai_responses_client.call_openai_responses(...)`
  - exit `0`
  - `ERR=0`, `TEXT=OK`

### Notes
- API usage count for this test: 1 request.

---

## Addendum (2026-02-21) - Diffpatch Success-Rate Benchmark

### Goal
- Benchmark diff patch generation success rate and choose a better prompt structure.

### Method
- Real API benchmark (`gpt-4.1-mini`) on temporary git repos.
- Each trial asks model to edit one line in `README.md`.
- Validation uses `tools.patch_first.apply_patch_safely` and post-apply content check.

### Verify
- round 1 benchmark (3 prompts x 3 trials):
  - exit `0`
  - result:
    - `minimal`: `0/3`
    - `structured`: `0/3`
    - `template`: `0/3`
  - dominant failures: `PATCH_GIT_CHECK_FAIL`, `PATCH_PARSE_INVALID`
- round 2 benchmark (3 prompts x 3 trials, stricter output contract):
  - exit `0`
  - result:
    - `structured_v2`: `3/3`
    - `aider_v2`: `3/3`
    - `skeleton_v2`: `3/3`
  - selected best: `skeleton_v2` (shortest/most stable format)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - exit `0`
  - workflow/contract/doc-index/lite-simlab/python-tests all pass

### Changes
- Updated prompt templates:
  - `agents/prompts/patchmaker_patch.md`
  - `agents/prompts/fixer_patch.md`
- Added benchmark record:
  - `meta/externals/20260221-diffpatch-prompt-benchmark.md`


---

## CTCP Team Run
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- Run folder (external): `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe`
- Prompt: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe/PROMPT.md`
- Trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe/TRACE.md`
- Questions: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\20260221-120322-prompt-source-probe/QUESTIONS.md`
