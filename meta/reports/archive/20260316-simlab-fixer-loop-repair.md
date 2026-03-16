# Report Archive - 2026-03-16 - SimLab fixer-loop 回归修复（S15 / S16）

## Readlist

- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`
- `scripts/ctcp_dispatch.py`
- `scripts/ctcp_orchestrate.py`
- `simlab/scenarios/S15_lite_fail_produces_bundle.yaml`
- `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`

## Plan

1. Bind a repair task scoped only to `S15` / `S16`.
2. Fix fixer request/prompt inputs so failed runs keep `failure_bundle.zip` visible.
3. Exempt managed pointer drift from the second-pass dirty-repo block without weakening real dirty protection.
4. Update issue memory for the recurring SimLab regression.
5. Re-run targeted SimLab scenarios and then canonical verify.
6. Record the new first failure point or full pass.

## Changes

- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/archive/20260316-simlab-fixer-loop-repair.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260316-simlab-fixer-loop-repair.md`

## Verify

- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (baseline) -> `1`
- first failure point:
  - gate: `lite scenario replay`
  - run_dir: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260316-153942`
  - summary: `passed=12`, `failed=2`
  - failed scenarios:
    - `S15_lite_fail_produces_bundle`: missing expected text `failure_bundle.zip`
    - `S16_lite_fixer_loop_pass`: missing expected text `"result": "PASS"`
- minimal fix strategy:
  - preserve `failure_bundle.zip` in fixer request missing-path inputs for blocked fixer patch paths
  - ignore managed `LAST_BUNDLE.txt` pointer drift when retrying a new fixer patch after a prior fail
- triplet command references:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

## Demo

- baseline verify summary: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\summary.json`
- `S15` trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\S15_lite_fail_produces_bundle\TRACE.md`
- `S16` trace: `C:\Users\sunom\AppData\Local\ctcp\runs\ctcp\simlab_runs\20260316-153942\S16_lite_fixer_loop_pass\TRACE.md`

## Questions

- None.
