# Demo Report — LAST

## Goal
- Diagnose why GitHub checks all failed quickly (~3s) for this repo.

## Readlist
- `ai_context/00_AI_CONTRACT.md`
  - Mandatory artifacts/report structure; verify-first and auditable delivery.
- `README.md`
  - Official verify entrypoints and doc-index contract.
- `BUILD.md`
  - Headless build prerequisites and expected build path.
- `PATCH_README.md`
  - Delivery/verification policy (`verify_repo` must pass).
- `TREE.md`
  - Current docs/spec structure reference.
- `docs/03_quality_gates.md`
  - Gate definition: workflow/contract/doc-index + lite replay.
- `ai_context/problem_registry.md`
  - Evidence-first verification requirement.
- `ai_context/decision_log.md`
  - No bypass/exemption recorded for this run.
- `.github/workflows/gate-matrix.yml`
  - Failing check job definition.
- `.github/workflows/verify.yml`
  - Failing verify jobs definition.

## Plan
1) Docs/Spec
- Read mandatory contract/docs and workflow definitions.
2) Code
- Default no code change; only switch to code fix if repo-side root cause is proven.
3) Verify
- Reproduce local gates and run `scripts/verify_repo.ps1`.
4) Report
- Record GitHub run evidence + local verification result.

## Timeline / Trace pointer
- Run pointer: `meta/run_pointers/LAST_RUN.txt`
- External run folder: `C:\Users\sunom\.ctcp\runs\ctcp\20260219-131720-github-checks-diagnosis`
- Trace: `C:\Users\sunom\.ctcp\runs\ctcp\20260219-131720-github-checks-diagnosis\TRACE.md`

## Changes
- `meta/tasks/CURRENT.md`
  - Replaced with task: GitHub checks failure diagnosis; recorded acceptance and results.
- `meta/externals/20260219-github-actions-failure-diagnosis.md`
  - Added external evidence from failing run pages and conclusion.
- `meta/run_pointers/LAST_RUN.txt`
  - Updated to this run's external trace directory.
- `meta/reports/LAST.md`
  - Updated to current diagnostic report.

## Verify
- GitHub run evidence (web):
  - `https://github.com/s1mplethings/ctcp/actions/runs/13722229574/job/38378107828`
  - `https://github.com/s1mplethings/ctcp/actions/runs/13722229572/job/38378107821`
  - Key annotation on both jobs: "Your account has been locked due to a billing issue with your payment method."
- Local command:
  - `python tools/checks/gate_matrix_runner.py`
  - Exit: `0`
- Local command:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`
  - Exit: `0`
- Mandatory gate:
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
  - Exit: `0`
  - Key output: `100% tests passed`, `[workflow_checks] ok`, `[contract_checks] ... ok`, `[sync_doc_links] ok`, `[verify_repo] OK`

## Open questions (if any)
- None.

## Next steps
- Fix GitHub account billing/payment issue, unlock Actions, then rerun failed checks.
- If checks still fail after unlock, diagnose repository-side logs per job.
