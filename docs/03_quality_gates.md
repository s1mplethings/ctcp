# Quality Gates (DoD)

If this file conflicts with `docs/00_CORE.md`, `docs/00_CORE.md` wins.

## 1) Single DoD Entrypoint

Only these commands are valid acceptance gate entrypoints:

- Windows: `scripts/verify_repo.ps1`
- Unix: `scripts/verify_repo.sh`

No alternative `scripts/verify.*` family is authoritative for DoD in this repo.

Verify is the canonical acceptance entrypoint, but it is not the product mainline. The product mainline is:
`ProjectIntent -> Spec -> Scaffold -> Core Feature Implementation -> Smoke Run -> Demo Evidence -> Delivery Package`.
The job of verify is to prove that this chain really produced a runnable MVP, not to substitute for that chain.

## 2) Verify Evidence Naming (Unified Contract)

- Canonical machine verify artifact (run_dir): `artifacts/verify_report.json`.
- `proof.json` is removed from hard DoD contract; it is not required by `verify_repo.*`.
- `verify_report.md` may exist as optional human summary, but it is non-authoritative.
- Running `verify_repo.*` directly decides pass/fail by command exit code + logs.
  For repo-level tasks, command/evidence summary MUST be recorded in `meta/reports/LAST.md`.

## 3) Current `verify_repo.*` Gate Sequence (Script-Aligned)

`scripts/verify_repo.ps1` and `.sh` currently execute gates in this order:

1. Anti-pollution gate
   - Fail if tracked/unignored build outputs exist in repo (`build*/**`).
   - Fail if tracked/unignored run outputs exist in repo (`simlab/_runs*/**`, `meta/runs/**`).
2. Headless lite build path (if CMake exists)
   - Configure/build the default headless target with `BUILD_TESTING=ON`.
   - Run lite `ctest` selector when test files exist.
3. Workflow gate
   - Run `python scripts/workflow_checks.py`.
4. Plan/scope/behavior contract gates
   - `python scripts/plan_check.py`
   - `python scripts/patch_check.py`
   - `python scripts/behavior_catalog_check.py`
5. Contract and doc index gates
   - `python scripts/contract_checks.py`
   - `python scripts/sync_doc_links.py --check`
6. Code health growth-guard gate (code profile)
   - `python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
7. Triplet integration guard gate
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
8. Lite replay + Python unit tests
   - `python simlab/run.py --suite lite` (unless `CTCP_SKIP_LITE_REPLAY=1`)
   - `python -m unittest discover -s tests -p "test_*.py"`
9. Plan declared-gate/evidence replay check
   - `python scripts/plan_check.py --executed-gates <csv> --check-evidence`

Passing all required steps is a DoD pass.
First non-zero step is the first failure point for repair.

## 4) Contract Lint Requirements

The following rule classes are part of contract acceptance and MUST be owned by the contract/doc/plan-evidence gates, even when they are not yet split into separate scripts:

1. Response/task-progress lint
   - Authority: `docs/11_task_progress_dialogue.md`
   - Blocking when a support/frontend-visible task contract violates first-sentence entry, forbidden phrase patterns, redundant goal echo, unnecessary question, or missing next action.
2. Documentation closure lint
   - Blocking when style / showcase / metadata truth changes are documented only in prompts, reports, or archive notes without updating the authoritative docs in the same patch.
3. Test showcase lint
   - Blocking when a task claims generated tests or user-visible demonstration but lacks `artifacts/test_plan.json`, `artifacts/test_cases.json`, `artifacts/test_summary.md`, `artifacts/demo_trace.md`, and `artifacts/screenshots/` or an explicit no-screenshot reason.
4. Metadata consistency lint
   - Authority: root `VERSION` plus provenance rules in `docs/30_artifact_contracts.md` and `docs/40_reference_project.md`
   - Blocking when run reports, scaffold/generated-project provenance, or human summaries that cite a version disagree with `VERSION`.
5. Persona regression lint
   - Authority: `docs/14_persona_test_lab.md` plus repo-local `persona_lab/` assets
   - Blocking when a patch changes task-progress dialogue, support reply style, or style-regression acceptance but does not update persona-lab rubrics/cases or explicitly record `persona_lab_impact: none`.
6. Project output completeness lint (project-generation tasks)
   - Authority: `docs/41_low_capability_project_generation.md`, `docs/30_artifact_contracts.md`, `docs/backend_interface_contract.md`
   - Blocking when project generation claims completion without explicit `ProjectIntent`, `Project Spec`, runnable scaffold/core-feature/smoke/delivery evidence, all three layers (source/doc/workflow), explicit `target/generated/missing/acceptance` file lists, or formal artifact interface readability (`list_output_artifacts`, `get_output_artifact_meta`, `read_output_artifact`, `get_project_manifest`).
7. Generic MVP validation lint
   - Blocking when a generated project lacks a runnable entrypoint, usable startup README, one core user flow, passing smoke-run evidence, or when it still looks like a placeholder skeleton.
8. Domain-specific validation lint
   - Domain rules must be isolated by project/domain type and must not silently redefine the generic MVP gate.
7. Output freeze sequencing lint (project-generation tasks)
   - Authority: `docs/04_execution_flow.md`, `docs/41_low_capability_project_generation.md`
   - Blocking when generated files are produced before `output_contract_freeze` artifacts are defined.

## 5) Failure Attribution for New Contract Lints

- Response/task-progress violations are blocking for support/frontend-visible contract work.
- Missing showcase artifacts are blocking only when the task claims testing/showing capability; a non-visual flow may omit screenshots only with an explicit recorded reason.
- Version mismatch is blocking; missing version in a note that makes no version claim is advisory.
- Persona regression asset drift is blocking when the patch changes style contracts, support lane style behavior, or style acceptance criteria.
- Conflicting legacy docs must be marked `deprecated` / `superseded` in the same patch rather than silently removed.
- Project-generation completion is blocking if any required layer/interface/manifest field is missing or unreadable.
- Generic MVP validation is blocking even when manifest/verify artifacts exist.
- Domain-specific validation may strengthen checks for a matched domain, but it must not leak into the generic gate for all projects.

## 6) Optional Full Gate

- Enable via `--full` or `CTCP_FULL_GATE=1`.
- Windows runs `scripts/test_all.ps1` when present.
- Unix runs `scripts/test_all.sh` when present.
- Missing full test script is logged as skip, not silent pass.

## 7) Contract Update Rule

If a failure class is not covered by current gates:

1. Add the check to `scripts/verify_repo.ps1` and `.sh` (or shared gate script invoked by both).
2. Add/adjust tests or scenarios so the new gate is reproducible.
3. Update this document and `docs/30_artifact_contracts.md` in the same patch.
4. If the failure class changes user-visible task dialogue, persona regression, showcase semantics, or project-generation completion rules, update the relevant routed contracts in the same patch (`docs/11_task_progress_dialogue.md`, `docs/14_persona_test_lab.md`, `docs/40_reference_project.md`, `docs/41_low_capability_project_generation.md`).
