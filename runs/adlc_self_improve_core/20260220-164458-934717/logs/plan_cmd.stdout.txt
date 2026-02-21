# PLAN - forge-full-suite self optimize (Round 1)

status: SIGNED  
label: BOOTSTRAP  
verify_rc: N/A

## Objective
Produce a minimal, auditable bootstrap plan and patch flow for `forge-full-suite self optimize`, strictly within policy.

## Constraints Snapshot
- policy: `contracts/allowed_changes.yaml`
- max_files: `10`
- max_added_lines: `800`
- max_deleted_lines: `800`
- max_total_lines: `800`
- allowed_paths: `scripts/`, `tools/`, `docs/`, `workflow_registry/`, `simlab/`, `tests/`, `contracts/`, `README.md`
- blocked_paths: `.github/`, `runs/`, `build/`, `dist/`

## Execution Plan
1. Docs/Spec: add or update one bootstrap spec file under `docs/` for goal, scope, constraints, and stop conditions.
2. Docs/Spec: add or update one workflow entry under `workflow_registry/` for Round 1 bootstrap tracking.
3. Code: default to no runtime behavior changes in Round 1.
4. Code fallback: if verification cannot pass without code edits, make at most one focused change in `scripts/` or `tools/`, directly tied to this goal.
5. Verify: run `python scripts/contract_checks.py`.
6. Verify: run `python scripts/workflow_checks.py`.
7. Verify: run `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (or `bash scripts/verify_repo.sh` on Unix).
8. Report/Patch: run the external PATCH command and emit unified diff only, with output beginning `diff --git`.

## Acceptance Steps
1. `python scripts/contract_checks.py` exits `0`.
2. `python scripts/workflow_checks.py` exits `0`.
3. `scripts/verify_repo.ps1` (or `scripts/verify_repo.sh`) exits `0`.
4. `git diff --name-only` lists only allowed paths.
5. `git diff --stat` stays within `max_files <= 10` and total changed lines `<= 800` (added `<= 800`, deleted `<= 800`).
6. External patch output first line matches `diff --git` and contains no prose before the diff.

## Patch Command Requirement
Use an external patch command template with `{PROMPT_PATH}` and `{REPO_ROOT}` placeholders, and require unified diff output only.
