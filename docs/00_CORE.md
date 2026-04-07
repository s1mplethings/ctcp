# CTCP Core Contract (v0.2)

This file is the authoritative runtime-truth contract source.

<!-- TOC (agent: jump to the section you need) -->

| # | Section | Anchor |
|---|---------|--------|
| 0.M | Markdown Object Lifecycle | [→](#0m-markdown-object-lifecycle-contract) |
| 0 | Runtime Truth Boundary | [→](#0-runtime-truth-boundary) |
| 0.V | Version and Metadata Truth | [→](#0v-version-and-metadata-truth-contract) |
| 0.W | 10-Step Flow Principle | [→](#0w-fixed-10-step-execution-flow-principle) |
| 0.X | Runtime Wiring Contract | [→](#0x-runtime-wiring-contract) |
| 0.Y | Frontend Bridge Rule | [→](#0y-frontend-to-execution-bridge-rule) |
| 0.Z | Conversation Mode Gate | [→](#0z-conversation-mode-gate) |
| 0.Z1 | Task-Progress Dialogue | [→](#0z1-task-progress-dialogue-contract) |
| 0.Z2 | Persona Test Lab | [→](#0z2-persona-test-lab-isolation-contract) |
| 1 | Core Positioning | [→](#1-core-positioning-headless-first) |
| 2 | Canonical Entrypoints | [→](#2-canonical-entrypoints-must) |
| 3–5 | Definitions / Locations / Roles | [→](#3-definitions) |
| 6 | Artifact Minimum Set | [→](#6-artifact-minimum-set) |
| 7 | Find Contract | [→](#7-find-contract-resolver-first) |
| 8 | Plan and Review Gate | [→](#8-plan-and-review-gate) |
| 9 | DoD Gate Contract | [→](#9-dod-gate-contract-verify_repo) |
| 9.1 | Verification Profiles | [→](#91-verification-profiles) |
| 10 | Stop Conditions | [→](#10-stop-conditions-must) |

<!-- /TOC -->

Source map (single source per concern):

- Repo purpose source: `docs/01_north_star.md`
- Agent main contract source: `AGENTS.md`
- Expanded execution flow source: `docs/04_execution_flow.md`
- Current task source: `meta/tasks/CURRENT.md`
- Runtime engineering truth source: `docs/00_CORE.md` (this file)
- Task-progress dialogue source: `docs/11_task_progress_dialogue.md`
- Persona test lab source: `docs/14_persona_test_lab.md`
- Repo version source: root `VERSION`
- Markdown object state source: `docs/10_REGISTRY.md`
- Markdown object transition source: `docs/20_STATE_MACHINE.md`

## 0.M Markdown Object Lifecycle Contract

The repository's process/strategy/interface/rule/implementation documents are managed as stateful objects.

Rules:
- Object state authority is `docs/10_REGISTRY.md`.
- Allowed state transitions are defined only in `docs/20_STATE_MACHINE.md`.
- Operational defaults:
  - `active`: only state allowed for default/runtime normative behavior.
  - `deprecated`: compatibility only; no new references.
  - `disabled`: off by default; explicit opt-in only.
  - `removed`: no repo/config/runtime references allowed.
  - `archived`: history only, non-runtime.
- Destructive jump is forbidden:
  - `active -> removed`
  - `active -> archived`
  - `deprecated -> archived`
- Removal path is mandatory:
  `active -> deprecated -> disabled -> removed -> archived`

## 0) Runtime Truth Boundary

All engineering progress is artifact-driven and auditable.
Runtime engineering truth comes from run artifacts + verify outputs + explicit reports.
User-visible chat, transient prompts, and vague notes are never runtime truth.

## 0.V Version and Metadata Truth Contract

Version and provenance claims MUST be traceable to one authority set.

Single authorities:
- repo version string: root `VERSION`
- run pass/fail: `artifacts/verify_report.json`
- current task scope: `meta/tasks/CURRENT.md`

Rules:
- Any run report, test summary, scaffold/reference metadata, or user-visible delivery summary that cites a version MUST copy `source_version` from `VERSION` verbatim.
- Provenance-bearing artifacts MUST pair `source_version` with `source_commit`; if git is unavailable, `source_commit=unknown` must be explicit.
- Version mismatch across `VERSION`, run/test reports, or generated project metadata is a contract failure.
- Missing version in purely local/transient notes is tolerated only when no version claim is made.

## 0.W Fixed 10-Step Execution Flow Principle

Repository modifications MUST follow the root 5-step flow in `AGENTS.md`.
`docs/04_execution_flow.md` keeps the expanded step mapping and detailed sequencing.
This file does not redefine step ordering.

## 0.X Runtime Wiring Contract

Any new capability is considered **not integrated** unless it satisfies all of the following:

1. **Upstream declared**
   - The feature MUST declare which entrypoint can trigger it.
   - Example entrypoints: support bot, frontend gateway, `scripts/ctcp_front_api.py`, `scripts/ctcp_orchestrate.py`.
2. **Downstream declared**
   - The feature MUST declare which next stage consumes its output.
   - A feature MUST NOT terminate in an internal side path unless that is the explicit final sink.
3. **Single source of truth declared**
   - The feature MUST declare which artifact or runtime state is authoritative.
   - User-visible chat memory is never the engineering source of truth.
   - CTCP run artifacts / run_dir / verify outputs remain authoritative for engineering state.
4. **Fallback path declared**
   - The feature MUST declare what happens when it fails, including:
     - whether it retries
     - whether it degrades
     - whether it asks the user for a decision
     - whether it blocks execution
5. **Acceptance path declared**
   - The feature MUST declare which test proves it is truly connected.
   - "File exists" or "module imports successfully" is not sufficient.
   - The acceptance test MUST prove the feature is reachable from its intended upstream entrypoint and that its output is consumed by the intended downstream stage.

If any of the above is missing, the feature is treated as **implemented but not integrated**.

## 0.Y Frontend-to-Execution Bridge Rule

Any user-visible capability that can:
- create a project run
- advance a project run
- submit a project decision
- upload an artifact for a project run
- query project execution state

MUST go through the frontend execution bridge.

Approved bridge path:
- `scripts/ctcp_front_bridge.py`
- `scripts/ctcp_front_api.py`

Disallowed:
- direct parallel execution paths inside support bot logic
- direct project mutation from frontend reply code
- hidden side routes that bypass the bridge and update execution state independently

A frontend feature that does not use the bridge is considered **not wired into CTCP**, even if it appears to work in isolation.

## 0.Z Conversation Mode Gate

Frontend conversation MUST classify the incoming turn before entering any project pipeline.

Minimum supported modes:
- GREETING
- SMALLTALK
- PROJECT_INTAKE
- PROJECT_DETAIL
- PROJECT_DECISION_REPLY
- STATUS_QUERY

Rules:
- GREETING and SMALLTALK MUST NOT enter planning / missing-info / tradeoff question logic.
- GREETING and SMALLTALK MAY still be answered by the configured support model; mode-gating forbids planning logic, not model routing.
- Project-manager mode MAY only activate when sufficient task signal exists.
- Internal error rewriting and project follow-up questions are forbidden when no valid active task summary exists.
- Task-like public replies MUST also satisfy the task-progress dialogue contract before emission.

A capability is not considered complete when it merely exists in code or docs.
It is only complete when:
- it is reachable from the intended entrypoint,
- its output is consumed by the intended downstream stage,
- its regression is recorded if it failed before,
- and its reusable nature has an explicit skill decision.

## 0.Z1 Task-Progress Dialogue Contract

Any user-visible task reply MUST bind to the current execution state before it is emitted.
Authoritative rule source: `docs/11_task_progress_dialogue.md`.

Minimum bound fields:
- current task goal
- current phase
- last confirmed items
- current blocker or `none`
- message purpose (`explain|progress|decision|failure|delivery`)
- whether a question is actually required
- next action
- proof refs when reporting tests, demos, screenshots, or packages

A reply that sounds natural but does not bind these fields is treated as ungrounded and incomplete.

## 0.Z2 Persona Test Lab Isolation Contract

Persona Test Lab is the authoritative isolated style-regression layer for the production assistant.
Authoritative rule source: `docs/14_persona_test_lab.md`.

Rules:
- Production assistant persona, test user personas, and judge/scoring layer MUST remain separate.
- Persona Test Lab MAY consume production dialogue contracts, but it MUST NOT mutate production conversation state or project run state.
- Every persona case MUST run in a fresh session with fixed assistant persona, fixed test user persona, fixed task input, and fixed turn limit or stop condition.
- Persona regression claims are incomplete unless transcripts, scores, and fail reasons are written to external persona-lab run artifacts.
- Persona lab run artifacts are evidence for style regression only; they do not replace production run truth or `artifacts/verify_report.json`.

## 1) Core Positioning (Headless First)

- Core path is headless and offline-first.
- Repository runtime/build surface does not ship a dedicated GUI target.
- Legacy GUI-era docs may remain only as deprecated historical material and are not runtime/build authority.

## 2) Canonical Entrypoints (MUST)

- Execution entrypoint: `scripts/ctcp_orchestrate.py`
- DoD gate entrypoints:
  - Windows: `scripts/verify_repo.ps1`
  - Unix: `scripts/verify_repo.sh`
- Legacy alternate execution or verify entry scripts are unsupported.

## 3) Definitions

- Repo: git repository. Must not track run/build outputs.
- Run Directory (Blackboard): external folder containing artifacts, trace, reviews, logs.
- Orchestrator: local driver that advances state by artifact presence and gate results; it does not decide strategy.
- TeamNet: multi-role artifact production model.
- ADLC: execution lifecycle. Execution starts only after signed `artifacts/PLAN.md`.

## 4) Locations (MUST)

- Run root MUST be outside repo, controlled by `CTCP_RUNS_ROOT`.
- Repo keeps only lightweight pointer files (for example `meta/run_pointers/LAST_RUN.txt`).
- Path details: `docs/21_paths_and_locations.md`.

## 5) Roles and Boundaries (MUST)

### 5.1 Local Roles

1. Local Orchestrator
   - MUST: create run_dir, emit events, gate on artifacts, run verify gate, trigger failure bundle flow.
   - MUST NOT: decide workflow strategy, write patch content, sign plan.
2. Local Librarian (hard-local-model, repo-scoped)
   - MUST: transform `artifacts/file_request.json` -> `artifacts/context_pack.json` through the local-model provider path (default `ollama_agent`).
   - MUST: fail fast when the local model is unavailable, returns empty output, or cannot be normalized into the context-pack contract.
   - MUST NOT: silently fall back to remote `api_agent` or report fake `context_pack` success.
   - MUST: keep evidence local to run artifacts (`step_meta.jsonl`, logs, target artifact) and surface the chosen provider/model in that evidence.
3. Local Verifier
   - MUST: execute gates and emit verify evidence.
   - MUST NOT: make planning decisions.

### 5.2 API Roles

1. Chair / Planner (sole decision authority)
   - MUST: write analysis, file_request, `PLAN_draft`, sign `PLAN`.
   - MUST: adjudicate adversarial reviews.
2. Researcher (optional web-find)
   - MAY: produce `artifacts/find_web.json` when enabled by guardrails.
   - MUST obey allowlist/budget/locator policy.
3. Contract Guardian
   - MUST: write `reviews/review_contract.md` with `Verdict: APPROVE|BLOCK`.
4. Cost Controller
   - MUST: write `reviews/review_cost.md` with `Verdict: APPROVE|BLOCK`.
5. Red Team (optional)
   - MAY: write `reviews/review_break.md`.
6. PatchMaker / Fixer
   - MUST: write only `artifacts/diff.patch` within signed PLAN scope.

## 6) Artifact Minimum Set

All artifacts below are run_dir-relative.

### 6.1 Pre-Execution Required

- `artifacts/guardrails.md`
- `artifacts/analysis.md`
- `artifacts/find_result.json`
- `artifacts/file_request.json`
- `artifacts/context_pack.json`
- `artifacts/PLAN_draft.md`
- `reviews/review_contract.md`
- `reviews/review_cost.md`
- `artifacts/PLAN.md` (signed)

### 6.2 Execution Required

- `artifacts/diff.patch`
- `TRACE.md`
- `artifacts/verify_report.json` (canonical machine verify artifact)
- `failure_bundle.zip` (required when verify fails)

### 6.3 Verify Naming Policy (Single Authority)

- Canonical verify artifact name: `artifacts/verify_report.json`.
- `proof.json` is not part of current hard contract and is not required by `verify_repo.*`.
- `verify_report.md` is optional human-readable summary only; it is non-authoritative.
- `verify_repo.ps1/.sh` are gate entry scripts; they decide pass/fail by exit code and command outputs.
  They do not themselves define `proof.json` as DoD evidence.

### 6.4 Test Design + Showcase Evidence (Conditional)

When a task claims generated tests, executed showcase flows, screenshots, or user-visible demo evidence, the run truth MUST also include:

- `artifacts/test_plan.json`
- `artifacts/test_cases.json`
- `artifacts/test_summary.md`
- `artifacts/demo_trace.md`
- `artifacts/screenshots/` or an explicit `screenshots_not_available_reason`

These artifacts do not replace `artifacts/verify_report.json`; they are the required extension for "tested and shown" claims.

### 6.5 Persona Test Lab Evidence (Conditional)

When a task claims isolated style regression coverage, receptionist-tone repair, multilingual stability verification, or persona-based dialogue scoring, the run truth MUST also include the persona-lab artifacts defined in `docs/14_persona_test_lab.md` and `docs/30_artifact_contracts.md`.

These artifacts MUST stay outside the repo under `CTCP_RUNS_ROOT`.

## 7) Find Contract (Resolver First)

### 7.1 Default Mode: `resolver_only` (MUST)

- Resolver inputs are local:
  - `workflow_registry/`
  - historical successful runs (if present)
- Resolver output authority is only `artifacts/find_result.json`.

### 7.2 Optional Mode: `resolver_plus_web` (MAY)

When guardrails sets `find_mode: resolver_plus_web`:

- Researcher MUST produce `artifacts/find_web.json` before PLAN signing.
- Web-find is constrained by allow domains, query/page budgets, and locator policy.
- `find_web.json` is candidate input only; final workflow authority remains `find_result.json`.

## 8) Plan and Review Gate

- Chair MUST produce `artifacts/PLAN_draft.md`.
- Contract Guardian and Cost Controller MUST each provide explicit verdicts:
  `APPROVE` or `BLOCK`.
- Chair MAY sign `artifacts/PLAN.md` only when required reviews are `APPROVE`.

## 9) DoD Gate Contract (`verify_repo.*`)

`verify_repo.ps1/.sh` MUST enforce repository acceptance gates.
Current required gate classes are:

1. Anti-pollution gate for tracked/unignored in-repo build/run outputs.
2. Headless lite build path (default target) when CMake is available.
3. Workflow gate (`scripts/workflow_checks.py`).
4. PLAN/patch/behavior contract gates:
   - `scripts/plan_check.py`
   - `scripts/patch_check.py`
   - `scripts/behavior_catalog_check.py`
5. Contract and doc index checks:
   - `scripts/contract_checks.py`
   - `scripts/sync_doc_links.py --check`
6. Code health growth-guard check (code profile):
   - `python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
7. Triplet integration guard tests:
   - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
   - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
8. Lite replay and unit tests:
   - `python simlab/run.py --suite lite` (unless explicitly skipped by env)
   - `python -m unittest discover -s tests -p "test_*.py"`
9. PLAN gate evidence replay check:
   - `scripts/plan_check.py --executed-gates ... --check-evidence`

Full suite (`CTCP_FULL_GATE=1` or `--full`) is optional extension.

### 9.1 Verification Profiles

`verify_repo.*` supports three risk-tiered profiles to reduce unnecessary
burden on low-risk changes while preserving full strictness for code paths.

Profile selection order: `--Profile` / `--profile` flag > `CTCP_VERIFY_PROFILE`
env var > auto-detect via `scripts/classify_change_profile.py`.

Default profile when detection is unavailable: `code` (strictest).

| Profile | Use Case | Gates Run |
|---------|----------|-----------|
| `doc-only` | Markdown, docs, meta, reports, archive, cleanup — no code paths affected | anti-pollution, workflow, plan, patch, contract (advisory), doc-index, plan-evidence |
| `contract` | Authoritative governance/workflow/runtime contract sources | anti-pollution, workflow, plan, patch, behavior-catalog, contract, doc-index, plan-evidence |
| `code` | Any code/integration/script/runtime/test/build change | All gates (current full behavior) |

Rules:
- `doc-only` skips: headless build, code health growth-guard, triplet guard, lite replay, python unit tests, behavior catalog.
- `contract` skips: headless build, code health growth-guard, triplet guard, lite replay, python unit tests.
- `code` skips nothing; preserves current strict behavior.
- Profile-skipped gates are recorded as executed (profile-skip) for plan evidence purposes.
- `CURRENT.md` and `LAST.md` workflow evidence remain mandatory across all profiles.
- Contract checks run in advisory (non-blocking) mode for `doc-only` profile.

### 9.2 Failure Attribution

Verification output MUST classify failures:

- **task-owned**: failure in a gate required by the current profile, caused by current changes.
- **preexisting (advisory)**: failure in a gate run in advisory mode; recorded but non-blocking.
- **skipped**: gate not applicable to current profile; noted in output for audit trail.

Preexisting advisory failures do not block a tightly scoped `doc-only` task.
All failures are recorded in the verification summary for audit purposes.

### 9.3 Cleanup Policy

Repository cleanup follows `docs/cleanup_policy.md`:
- Archive-first for knowledge assets (docs, meta, decision logs).
- Hard delete only for generated artifacts, caches, temp outputs.
- Evidence required for any cleanup action.
- Protected paths may not be hard-deleted.

## 10) Stop Conditions (MUST)

Chair MUST define in PLAN:

- max iterations
- max files/bytes for context request
- max API calls (if relevant)
- stop on repeated same failure
- stop on scope violation
