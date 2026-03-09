# CTCP Core Contract (v0.2)

If this file conflicts with other docs, precedence is:
`docs/00_CORE.md` > `AGENTS.md` > `ai_context/00_AI_CONTRACT.md`.

## 0) Purpose

CTCP is a contract-first ADLC loop:
`doc -> analysis -> find -> context_pack -> plan -> [build <-> verify] -> contrast -> fix -> deploy/merge`.

All progress is artifact-driven and auditable.
Execution evidence lives in an external run directory ("Blackboard"), not in repo.

## 1) Core Positioning (Headless First)

- Core path is headless and offline-first.
- GUI/Inspector/graph visualization are optional add-ons.
- Optional GUI paths MUST NOT be required by the default DoD gate.

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
2. Local Librarian (read-only, deterministic)
   - MUST: transform `artifacts/file_request.json` -> `artifacts/context_pack.json` deterministically.
   - MUST: inject mandatory contracts first (see `docs/30_artifact_contracts.md` B.1), then process `needs[]` in order.
   - MUST: copy verbatim repo content only; no invented/summarized content.
   - MUST: remain local, repo-scoped, read-only (no network, no repo writes).
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
2. Headless lite build path (`CTCP_ENABLE_GUI=OFF`) when CMake is available.
3. Workflow gate (`scripts/workflow_checks.py`).
4. PLAN/patch/behavior contract gates:
   - `scripts/plan_check.py`
   - `scripts/patch_check.py`
   - `scripts/behavior_catalog_check.py`
5. Contract and doc index checks:
   - `scripts/contract_checks.py`
   - `scripts/sync_doc_links.py --check`
6. Lite replay and unit tests:
   - `python simlab/run.py --suite lite` (unless explicitly skipped by env)
   - `python -m unittest discover -s tests -p "test_*.py"`
7. PLAN gate evidence replay check:
   - `scripts/plan_check.py --executed-gates ... --check-evidence`

Full suite (`CTCP_FULL_GATE=1` or `--full`) is optional extension.

## 10) Stop Conditions (MUST)

Chair MUST define in PLAN:

- max iterations
- max files/bytes for context request
- max API calls (if relevant)
- stop on repeated same failure
- stop on scope violation
