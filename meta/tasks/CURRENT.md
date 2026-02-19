# Task — github-actions-all-failed-diagnosis

## Context
- User reported all GitHub checks failed quickly (about 3 seconds).
- Need identify whether failure is repository code/gate issue or external CI/account issue.
- Provide auditable evidence and local verification outcome.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): meta/externals/20260219-github-actions-failure-diagnosis.md
- [ ] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec: read required contract/docs + workflow files
2) Research-first: inspect latest GitHub Actions run pages and annotations
3) Verify: run local gate commands, then `scripts/verify_repo.ps1`
4) Report: update `meta/reports/LAST.md` with evidence and conclusion

## Notes / Decisions
- Default strategy: no code change unless a repository-side root cause is proven.
- If root cause is external (account/billing/policy), report mitigation steps without code edits.

## Results
- GitHub Actions run pages show the same job annotation: account locked due billing issue.
- Local `gate_matrix_runner.py`, `verify.ps1`, and `verify_repo.ps1` all passed on this machine.
- Root cause classified as external CI account/billing state, not repository workflow/code regression.
