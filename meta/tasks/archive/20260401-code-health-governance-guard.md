# Task - code-health-governance-guard

## Queue Binding

- Queue Item: `ADHOC-20260401-code-health-governance-guard`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: repo currently has multiple 1000+ and 3000+ files, including 5000+ entrypoint files, and lacks hard anti-expansion checks.
- Dependency check: `ADHOC-20260401-c224a08-decoupling-interface-closure = doing` (non-blocking for governance setup).
- Scope boundary: build detector + gate + governance docs + split backlog only; no broad product refactor.

## Task Truth Source (single source for current task)

- task_purpose: Establish repository-level code health governance to detect god files and block further expansion before deep refactoring.
- allowed_behavior_change:
  - `scripts/code_health_check.py`
  - `meta/code_health/rules.json`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `docs/rules/RULE-code-health-growth-guard.md`
  - `meta/backlog/code_health_backlog.md`
  - `.github/workflows/code-health.yml`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- forbidden_goal_shift: Do not execute broad code decomposition in this patch; only detection and governance constraints.
- in_scope_modules: `scripts/`, `docs/`, `meta/`, `simlab/`, `tests/fixtures/`.
- out_of_scope_modules: runtime business flow implementation and unrelated feature logic.
- completion_evidence: detector output with ranked risk list + verify gate wiring + governance docs/backlog + canonical verify attempt evidence.

## Analysis / Find (before plan)

- Entrypoint analysis: current largest hotspots are concentrated in entry and orchestration files (`scripts/ctcp_support_bot.py`, `scripts/ctcp_orchestrate.py`).
- Downstream consumer analysis: CI/verify gate is the only reliable enforcement point for anti-expansion.
- Source of truth: `meta/code_health/rules.json` + `scripts/code_health_check.py` + canonical verify scripts.
- Current break point / missing wiring: there is no blocking growth guard in `verify_repo.*` for oversized files or long-function growth.
- Repo-local search sufficient: yes.
- If no, external research artifact: none.

## Integration Check (before implementation)

- upstream: user request for code health governance and anti-god-file mechanism.
- current_module: `scripts/code_health_check.py` and `scripts/verify_repo.*`.
- downstream: `verify_repo.*` execution and CI workflows invoking canonical verify.
- source_of_truth: generated metrics report and verify gate exit code.
- fallback: if canonical verify fails, record first failure point and minimal fix strategy in `meta/reports/LAST.md`.
- acceptance_test:
  - `python scripts/code_health_check.py --top 40 --output-json .agent_private/code_health_report.json --output-md .agent_private/code_health_report.md`
  - `python scripts/code_health_check.py --enforce --changed-only --baseline-ref HEAD`
  - `python scripts/workflow_checks.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not claim healthy status from line count only
  - do not skip mixed-responsibility and churn checks
  - do not skip canonical verify attempt evidence
- user_visible_effect: repo now has a machine-enforced no-growth guard for oversized files and a prioritized split backlog.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: A repository code-health detector reports per-file total/code/import/function/max-function/churn and outputs risk ranking.
- [x] DoD-2: Canonical verify gate includes a code-health growth-guard check to block oversized file expansion on code profile.
- [x] DoD-3: A code-health backlog and repository growth-guard rule document define minimal split order and module boundaries for high-risk files.

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): not needed, repo-local data sufficient
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Build a code-health scanner with multi-factor risk scoring.
2) Add a configurable rule set for thresholds and exclusions.
3) Wire scanner enforcement into canonical verify scripts.
4) Run scan and produce high-risk ranking evidence.
5) Write anti-expansion rule and decomposition backlog.
6) Run workflow checks and canonical verify.
7) Capture check/contrast/fix loop evidence and first failure point if any.
8) Completion criteria: prove `connected + accumulated + consumed`.

## Notes / Decisions

- Default choices made: enforce growth-guard on changed files for code profile only; keep doc-only/contract profiles lightweight.
- Alternatives considered: hard-failing all historical oversized files now (rejected due immediate repo-wide blockade).
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- issue memory decision: no new user-visible runtime defect class; governance debt captured in `meta/backlog/code_health_backlog.md`.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: no, because this is a repo-specific governance policy, not a reusable cross-repo workflow package yet.`

## Check / Contrast / Fix Loop Evidence

- check: first enforcement run flagged long-function and oversized growth violations in current dirty workspace.
- contrast: guard should prevent further expansion but not require one-shot full legacy cleanup.
- fix: enforcement now compares against baseline and blocks growth, while backlog defines staged decomposition; S16 lite replay fixture/scenario was minimally stabilized so canonical verify can complete.

## Completion Criteria Evidence

- connected: scanner -> verify gate wiring in both `verify_repo.ps1` and `verify_repo.sh`.
- accumulated: risk metrics + thresholds + backlog recorded in docs/meta artifacts.
- consumed: verify scripts now consume scanner results as a blocking gate in code profile.

## Results

- Files changed:
  - `scripts/code_health_check.py`
  - `meta/code_health/rules.json`
  - `scripts/verify_repo.ps1`
  - `scripts/verify_repo.sh`
  - `docs/00_CORE.md`
  - `docs/03_quality_gates.md`
  - `docs/rules/RULE-code-health-growth-guard.md`
  - `meta/backlog/code_health_backlog.md`
  - `.github/workflows/code-health.yml`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `simlab/scenarios/S16_lite_fixer_loop_pass.yaml`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- Verification summary: scanner/workflow checks + lite replay passed; canonical `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` returned `0`.
- Queue status update suggestion (`todo/doing/done/blocked`): `done` (governance mechanism landed and verify gate closed green).
