# Runtime ADLC Pipeline Contract (Execution Lane)

Scope boundary:

- This file defines runtime ADLC execution inside a run (orchestrator lane).
- This file is NOT the canonical repository modification workflow.
- Canonical repository workflow source: `docs/04_execution_flow.md`.

## Runtime ADLC Mainline

`doc -> analysis -> find -> context_pack -> plan -> [build<->verify] -> contrast -> fix -> deploy/merge`

Execution starts only after signed `artifacts/PLAN.md`, required adversarial reviews are `APPROVE`, and `artifacts/context_pack.json` exists.

## Canonical Entrypoint

- Only `scripts/ctcp_orchestrate.py` is supported for execution.
- Legacy alternate entry scripts no longer exist and are unsupported.
- Frontend/user-facing lanes must not bypass this runtime mainline.

## Step I/O Contract (MUST)

| Step | MUST Inputs | MUST Outputs | Owner |
|---|---|---|---|
| `doc` | Goal + hard constraints | `artifacts/guardrails.md` | Chair/Planner |
| `analysis` | guardrails + scoped context | `artifacts/analysis.md`, `artifacts/file_request.json` | Chair/Planner |
| `find` | goal + `workflow_registry/index.json` + historical successful runs | `artifacts/find_result.json` | Resolver (under Chair policy) |
| `context_pack` | `artifacts/file_request.json` | `artifacts/context_pack.json` | Local Librarian |
| `plan` | analysis + find result + context pack + reviews | `artifacts/PLAN_draft.md`, signed `artifacts/PLAN.md` | Chair/Planner |
| `[build<->verify]` | signed plan + patch | `TRACE.md`, `artifacts/verify_report.json` | Local Verifier |
| `contrast` | verify report + trace | `failure_bundle.zip` (if fail) | Local Verifier |
| `fix` | failure bundle + signed plan scope | `artifacts/diff.patch` | PatchMaker/Fixer |
| `deploy/merge` | passing verify + final decision | `artifacts/release_report.md` | Chair/Planner |

### Hard gate rule for `context_pack`

- Orchestrator/dispatcher MUST block plan signing and execution until `artifacts/context_pack.json` exists.
- If context_pack is missing, dispatcher MUST route to deterministic local Librarian execution by default (`scripts/ctcp_librarian.py`).
- Manual outbox for librarian is allowed only under explicit `mode: manual_outbox` configuration.

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

## Frontend Gateway Flow (Presentation Layer Only)

Frontend conversational flow must remain a shell over CTCP:

1. frontend receives user message / attachments
2. frontend calls `ctcp_front_bridge` operation (`ctcp_new_run`, `ctcp_get_status`, `ctcp_advance`, etc.)
3. CTCP orchestrator (`scripts/ctcp_orchestrate.py`) remains the only execution driver
4. frontend reads run artifacts and renders user-facing progress/decision prompts
5. when decision is needed, frontend writes only requested target artifact through `ctcp_submit_decision`
6. frontend resumes execution by calling `ctcp_advance`

Frontend must not become a second workflow engine and must not claim engineering progress without run artifact evidence.
