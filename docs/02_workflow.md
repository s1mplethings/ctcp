# Runtime ADLC Pipeline Contract (Execution Lane)

Scope boundary:

- This file defines runtime ADLC execution inside a run (orchestrator lane).
- This file is NOT the canonical repository modification workflow.
- Canonical repository workflow source: `docs/04_execution_flow.md`.

## Runtime ADLC Mainline

`doc -> analysis -> find -> context_pack -> plan -> [build<->verify] -> contrast -> fix -> deploy/merge`

Execution starts only after signed `artifacts/PLAN.md`, required adversarial reviews are `APPROVE`, and `artifacts/context_pack.json` exists.

## Unique Default Runtime Mainline

The default CTCP runtime mainline is singular. Specialized lanes may keep their own artifacts, but they must report into this mainline:

`goal/task input -> librarian/context_pack -> ADLC phase judgment + plan/gate -> execution lane -> whiteboard progress emission -> frontend/backend bridge consumption -> delivery/gate result -> run_manifest finalization`

Default responsibilities:

- Librarian is the context-entry layer. It turns scoped `file_request.json` input into `context_pack.json` and blocks downstream planning when context is missing or invalid.
- ADLC is the unified orchestration layer. It owns phase judgment, gate status, result summary, and first failure reporting for every lane, including project-generation lanes with specialized artifact pipelines.
- Whiteboard is the runtime-visible progress layer. It records support turns, librarian lookups, dispatch lookups, and dispatch results as an append-only run artifact.
- Bridge is the external consumption layer. Frontend/support clients consume run state, decisions, support context, whiteboard snapshots, and output artifact metadata only through bridge interfaces.
- `artifacts/run_manifest.json` is the run-level truth source. It summarizes whether Librarian, ADLC, Whiteboard, and Bridge participated in the same run and records final status or first failure.
- `artifacts/run_responsibility_manifest.json` is the only responsibility ledger. It records goal/entry/workflow/provider/API/fallback/final-producer/final-verdict accountability for the run.

### Responsibility Split Table

| Flow | Input | Output | Required Artifact / Fields | Failure Condition |
|---|---|---|---|---|
| Librarian | `artifacts/file_request.json` and repo files | scoped context pack | `artifacts/context_pack.json`; `run_manifest.context_pack_present=true` | missing/invalid request, denied path, budget breach, invalid context-pack contract |
| ADLC | goal, context pack, lane artifacts, gate results | phase, gate status, result summary, first failure | `run_manifest.adlc_phase`, `run_manifest.adlc_gate_status`, `run_manifest.gates_passed`, `run_manifest.first_failure_*` | required context/plan/gate missing, verify failure, max iterations, invalid lane result |
| Whiteboard | support turns, librarian lookup query, dispatch request/result | append-only progress state | `artifacts/support_whiteboard.json`; `run_manifest.whiteboard_present=true` | missing whiteboard write after support/dispatch activity, malformed entries, unbounded growth |
| Bridge | frontend/support operation and run id | client-visible payload derived from run artifacts | bridge output refs in `run_manifest.bridge_output_refs`; `bridge_present` / `bridge_output_present` | direct run mutation outside bridge, invented state, missing formal artifact/status payload |

### ADLC as Unified Orchestration Layer

ADLC is not limited to `workflow_registry/adlc_self_improve_core/recipe.yaml`.
That recipe remains one implementation lane. The ADLC contract is the orchestration layer above all lanes.

Every lane MUST report these fields into `artifacts/run_manifest.json`:

- current phase
- gate status
- result summary through `final_status`
- first failure gate and reason when failed

Project-generation may keep its project-spec, capability, sample-generation, and refinement artifacts, but it is still required to surface the current phase, gate result, and final status through the ADLC/run-manifest layer.

## Canonical Product Mainline

For project-generation tasks, the only product mainline is:

`Goal -> Intent -> Spec -> Scaffold -> Core Feature -> Smoke Verify -> Demo Evidence -> Delivery Package`

Rules:

- canonical workflow id for product generation: `wf_project_generation_manifest`
- `pipeline_contract.source_contract` must be `docs/02_workflow.md`
- capability/sample/refinement remain support artifacts; they must not become parallel stage truth

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
- If context_pack is missing, dispatcher MUST route to `librarian/context_pack` through `api_agent` on the mainline.
- `librarian/context_pack` is hard-locked to `api_agent` on the mainline (`mock_agent` mode remains test-only).
- Manual outbox, local providers, and `CTCP_FORCE_PROVIDER` MUST NOT bypass that hard lock.

### Formal API-only Rule (`CTCP_FORMAL_API_ONLY=1`)

- For formal runs, every critical stage (including `librarian/context_pack`) must resolve to `api_agent`.
- Local fallback or local function execution on critical stages cannot be counted as formal PASS.

## Standard Artifact Paths

- External run root (must be outside repo): `${CTCP_RUNS_ROOT}/<repo_slug>/<run_id>/`
- Run artifacts: `${run_dir}/artifacts/*`
- Run manifest truth source: `${run_dir}/artifacts/run_manifest.json`
- Responsibility ledger (single source for accountability): `${run_dir}/artifacts/run_responsibility_manifest.json`
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
