# Task - Medium Success Expansion

## Queue Binding

- Queue Item: `ADHOC-20260518-medium-success-expansion`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- Phase 21B staged medium candidate pipeline passed with two cases.
- Current medium outcomes are `inventory=repaired` and `knowledge_base=fallback`.
- The next blocker is breadth: medium provider candidate success must expand from 2 cases to at least 4 cases without adding dedicated deterministic fast paths.

## Task Truth Source

- task_purpose:
  - Expand live provider medium project benchmark to at least four cases.
  - Add `live_provider_event_booking_app` and `live_provider_invoice_manager_app`.
  - Preserve staged provider plan -> manifest -> batch synthesis -> assembly -> validation -> max-one targeted repair.
  - Add medium project contract evidence and validation.
- required_runtime_chain:
  - `new-run -> status -> advance -> analysis -> source_generation -> project_output -> generated tests -> runtime validation`.
- allowed_behavior_change:
  - Add medium case metadata, fixture files, runtime validators, contract artifacts, attribution fields, tests, diagnostics, and Review Pack Phase 22 summary.
  - Improve medium prompt/contract context and route/store/frontend/test consistency validation.
- forbidden_goal_shift:
  - No medium dedicated deterministic fast path.
  - No fixture lowering or validator weakening.
  - No agent-project/scaffold substitution.
  - No fake accepted/repaired/provider ratio.
  - No validation bypass or unbounded repair loop.
- in_scope_modules:
  - medium provider candidate pipeline.
  - medium benchmark fixtures/validators/tests.
  - medium attribution and Review Pack evidence.
- out_of_scope_modules:
  - agent runtime/planner/web capability.
  - large project generation.
  - orchestrator rewrites.
  - benchmark fixture lowering.
- completion_evidence:
  - medium benchmark pass with at least four cases.
  - blind matrix pass.
  - full regression pass.
  - unittest discover pass.
  - repo verification pass.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_medium_candidate.py`
  - `tools/providers/project_generation_live_full_candidate.py`
  - `tools/providers/project_generation_live_candidate_helpers.py`
  - `tools/providers/project_generation_candidate_validation.py`
  - `tools/providers/project_generation_attribution.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tests/live_provider_medium_project_benchmark/`
  - `tests/test_live_provider_medium_project_benchmark.py`
  - `tests/test_live_provider_medium_project_attribution.py`
  - `tests/test_live_provider_medium_project_validation.py`
  - `tests/test_live_provider_medium_project_safety.py`
  - `tests/test_live_provider_medium_project_review_pack.py`
  - `tests/test_live_provider_medium_candidate_staged_pipeline.py`
  - `tests/test_live_provider_medium_candidate_batching.py`
  - `tests/test_medium_project_contract_validation.py`
  - `tests/test_event_booking_medium_generation.py`
  - `tests/test_invoice_manager_medium_generation.py`
  - `meta/reports/REVIEW_PACK.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/CURRENT.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/archive/20260518-medium-success-expansion.md`
  - `meta/reports/archive/20260518-medium-success-expansion.md`
  - `artifacts/PLAN.md`
- Protected Paths:
  - `.git`
  - benchmark fixtures and validators outside medium benchmark scope
  - agent runtime/planner/web files
  - orchestrator/security/repo verification broad rewrites
  - provider credentials/secrets
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- explicit elevation signal: none; no frozen-kernel elevation required.
- forbidden bypass: no agent-project/scaffold substitution, no benchmark fixture lowering, no validation bypass, no fake provider metrics.
- acceptance checks: targeted medium benchmark/tests, blind matrix, full regression, unittest discover, workflow/module/patch/code-health checks, verify_repo.

## Analysis / Find

- Existing medium benchmark has 2 cases and passes with one repaired provider candidate plus one fallback.
- Phase 22 must expand the benchmark to at least 4 cases and require at least 2 accepted/repaired medium outcomes.
- Contract consistency must become visible through `artifacts/medium_project_contract.json`.

## Plan

1. Add event booking and invoice manager medium case metadata and fixtures.
2. Extend medium fallback baseline only as honest fallback, not a dedicated success path.
3. Generate and validate medium project contract artifacts for all medium cases.
4. Extend medium benchmark runtime validators and pass rules to four cases.
5. Add focused tests for contract validation, new cases, attribution, safety, and review pack.
6. Run targeted medium checks, then blind matrix, then full regression only if medium passes.

## Integration Check (before implementation)

- upstream: ordinary `new-run/status/advance` and analysis/source_generation artifacts.
- current_module: medium provider candidate staged synthesis, contract generation, validation, and benchmark expansion.
- downstream: project_output, generated tests, runtime validation, attribution, benchmark reports, and Review Pack.
- source_of_truth: user Phase 22 task plus active task card.
- fallback: deterministic fallback remains honest and does not count as provider medium success.
- acceptance_test: medium benchmark, blind matrix, full regression, unittest discover, workflow/module/patch/code-health checks, and verify_repo.
- forbidden_bypass: no agent-project/scaffold substitution, no medium dedicated fast path, no fixture lowering, no validation bypass.
- user_visible_effect: CTCP can validate more live-provider medium project candidates with transparent provider/fallback attribution.

## Check / Contrast / Fix Loop Evidence

- Check: Phase 21B passed but only covered two medium cases, with one fallback.
- Contrast: Phase 22 requires at least four medium cases, at least two accepted/repaired outcomes, and fallback_count <= 1.
- Fix: add two medium cases, contract consistency evidence, stronger validators, and updated gate metrics.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: provider plan -> manifest -> file batches -> medium contract -> project_output -> validation -> attribution/report.
- accumulated: benchmark summaries, attribution JSON, Review Pack, and LAST report carry the result forward.
- consumed: tests and benchmark pass rules consume case count, candidate count, authored file ratio, fallback evidence, and medium contract paths.

## Issue Memory Decision Evidence

- no new issue-memory entry: this is a bounded benchmark expansion and capability hardening task with dedicated regression coverage.

## Acceptance Checks

- [ ] medium benchmark includes at least 4 cases.
- [ ] event booking case exists.
- [ ] invoice manager case exists.
- [ ] staged pipeline still used.
- [ ] provider plan requested for every case.
- [ ] manifest validated for every case.
- [ ] file batches generated.
- [ ] `medium_project_contract.json` generated.
- [ ] accepted/repaired provider_authored_file_ratio >= 0.6.
- [ ] fallback_count <= 1.
- [ ] failed_count == 0.
- [ ] Review Pack includes Phase 22 summary.
- [ ] ordinary `new-run/status/advance` preserved.
- [ ] no agent-project/scaffold used.
- [ ] no medium dedicated deterministic fast path added.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: gated CTCP implementation with task binding, scoped patch, benchmark evidence, and repo reporting.
