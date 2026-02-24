CTCP Core Contract (v0.1)
0. Purpose

CTCP is a contract-first engineering loop:
doc -> analysis -> find -> plan -> [build <-> verify] -> contrast -> fix -> deploy/merge
All progress is driven by artifacts stored in the run directory ("Blackboard").

1. Definitions

Repo: the git repository (must remain clean; no run/build outputs tracked).

Run Directory (Blackboard): an external folder (NOT inside repo) that contains artifacts, traces, reviews, logs.

Orchestrator: local driver that advances the run by checking artifact presence and running verification. It does not decide plans.

TeamNet: multi-agent team roles that write specific artifacts before execution begins.

ADLC: the execution lifecycle; only enters execution after plan is signed.

Canonical Entrypoint (must)

- The only execution entrypoint is `scripts/ctcp_orchestrate.py`.
- Other legacy execution entry scripts are removed and unsupported.
- The only acceptance gate entrypoints are `scripts/verify_repo.ps1` and `scripts/verify_repo.sh`.

2. Locations (must)

Run directory root MUST be outside the repo, controlled by CTCP_RUNS_ROOT.

Repo MUST only contain lightweight pointers to last run (meta/run_pointers/LAST_RUN.txt).

See docs/21_paths_and_locations.md.

3. Roles and Permissions (must)
Local roles

Local Orchestrator (driver)

MUST: create run_dir, emit events, gate on artifact presence, run verify, generate failure bundle.

MUST NOT: choose workflow strategy, write patch content, approve plan.

Local Librarian (read-only)

MUST: provide minimal context packs based on Chair's file_request.

MUST NOT: decide, propose solutions, modify code.

Local Verifier (fact judge)

MUST: run gates, produce TRACE + verify_report, produce failure bundle on failure.

MUST NOT: decide.

API roles

Chair / Planner (only decision authority)

MUST: write analysis, file_request, PLAN_draft, sign PLAN.

MUST: adjudicate adversarial reviews.

Researcher (optional web-find)

MAY: produce find_web.json if enabled by guardrails.

MUST follow web policy (allowlist/budget/locator).

Contract Guardian (adversarial)

MUST: produce reviews/review_contract.md (APPROVE/BLOCK).

Cost Controller (adversarial)

MUST: produce reviews/review_cost.md (APPROVE/BLOCK).

Red Team (adversarial, optional)

MAY: produce reviews/review_break.md.

PatchMaker / Fixer (execute)

MUST: write only diff.patch within plan scope.

4. Artifacts (must exist before execution)

All artifacts live under the external run directory.

4.1 Required artifacts (pre-execution)

artifacts/guardrails.md

artifacts/analysis.md

artifacts/find_result.json

artifacts/file_request.json

artifacts/context_pack.json

artifacts/PLAN_draft.md

reviews/review_contract.md

reviews/review_cost.md

artifacts/PLAN.md (signed)

4.2 Required artifacts (execution)

artifacts/diff.patch

TRACE.md

artifacts/verify_report.json

failure_bundle.zip (only on failure)

5. Find (resolver-first; web-find optional)
5.1 Default: resolver-only (must)

find MUST resolve the best existing workflow from local sources:

workflow_registry/

historical successful runs (if present)

Output MUST be artifacts/find_result.json.

5.2 Optional: resolver + web-find (may)

If guardrails.md sets find_mode: resolver_plus_web:

Researcher MUST produce artifacts/find_web.json before plan can be signed.

Web-find MUST be constrained by allow_domains, budget, and locator rules.

Web-find is input only; final decision MUST still be find_result.json.

6. Plan and Reviews (must)

Chair MUST write PLAN_draft.md.

Contract Guardian and Cost Controller MUST review and write:

Verdict: APPROVE or Verdict: BLOCK

Chair MUST sign PLAN.md only after both are APPROVE.

7. Gates and Verification (must)

Lite verification MUST exist and MUST NOT be a "no-scenarios PASS".

verify_repo MUST fail if:

build outputs are tracked by git

run outputs appear inside repo

verify_repo MUST produce actionable output for fix loop.

8. Stop Conditions (must)

Chair MUST specify in plan:

max iterations

max files/bytes requested

max api calls (if relevant)

stop on repeated same failure

stop on scope violation
