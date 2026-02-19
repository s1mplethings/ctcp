# Workflow Contract (ADLC Primary)

If this file conflicts with `docs/00_CORE.md`, `docs/00_CORE.md` wins.

## ADLC Mainline

`doc -> analysis -> find -> plan -> [build<->verify] -> contrast -> fix -> deploy/merge`

Execution starts only after signed `artifacts/PLAN.md` and required adversarial reviews are `APPROVE`.

## Step I/O Contract (MUST)

| Step | MUST Inputs | MUST Outputs | Owner |
|---|---|---|---|
| `doc` | Goal + hard constraints | `artifacts/guardrails.md` | Chair/Planner |
| `analysis` | guardrails + scoped context | `artifacts/analysis.md`, `artifacts/file_request.json` | Chair/Planner |
| `find` | goal + `workflow_registry/index.json` + historical successful runs | `artifacts/find_result.json` | Resolver (under Chair policy) |
| `plan` | analysis + find result + reviews | `artifacts/PLAN_draft.md`, signed `artifacts/PLAN.md` | Chair/Planner |
| `[build<->verify]` | signed plan + patch | `TRACE.md`, `artifacts/verify_report.json` | Local Verifier |
| `contrast` | verify report + trace | `failure_bundle.zip` (if fail) | Local Verifier |
| `fix` | failure bundle + signed plan scope | `artifacts/diff.patch` | PatchMaker/Fixer |
| `deploy/merge` | passing verify + final decision | `artifacts/release_report.md` | Chair/Planner |

## Standard Artifact Paths

- External run root (must be outside repo): `${CTCP_RUNS_ROOT}/<repo_slug>/<run_id>/`
- Run artifacts: `${run_dir}/artifacts/*`
- Reviews: `${run_dir}/reviews/*`
- Trace: `${run_dir}/TRACE.md`
- Failure bundle: `${run_dir}/failure_bundle.zip` (only on failure)
- Repo pointer only: `meta/run_pointers/LAST_RUN.txt` (absolute run path)

## find vs web-research Boundary

- `find` is a resolver, not a search engine.
- Resolver primary inputs:
  - `workflow_registry/index.json`
  - local historical successful runs
- Resolver output authority:
  - `artifacts/find_result.json` is the only workflow selection authority for `plan`.
- Web research is optional and offline-oriented:
  - Researcher writes `meta/externals/<goal_slug>/externals_pack.json`
  - content can be transformed into candidate notes for plan review
  - it cannot replace resolver selection and cannot block the core offline loop

## Integration Rule for Externals

When `externals_pack` exists, it is treated as candidate evidence only:

1. Chair may cite it in `PLAN_draft.md` as implementation options.
2. Resolver selection (`selected_workflow_id`) remains from `find_result.json`.
3. If externals conflict with local contracts, contracts win and externals are discarded.
