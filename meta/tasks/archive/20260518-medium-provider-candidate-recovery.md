# Task - Medium Provider Candidate Recovery

## Queue Binding

- Queue Item: `ADHOC-20260518-medium-provider-candidate-recovery`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- Phase 20 blind candidate acceptance hardening passed with `accepted=2`, `repaired=3`, `fallback=0`, `failed=0`.
- Phase 21 medium benchmark ran but failed because both medium cases reached runnable output only through fallback.
- The current blocker is medium provider candidate construction: provider output must become parseable, attributable, and repairable enough that at least one medium case is accepted or repaired with provider-authored file ratio `>=0.6`.

## Task Truth Source

- task_purpose:
  - Implement Phase 21B staged medium provider candidate pipeline: provider plan, manifest validation, batched file synthesis, assembly, validation, and max-one targeted repair.
  - Keep fallback honest and do not count fallback as provider medium success.
  - Keep ordinary `new-run/status/advance -> analysis -> source_generation -> project_output -> generated tests -> runtime validation`.
- required_runtime_chain:
  - `new-run -> status -> advance -> analysis -> source_generation -> project_output -> generated tests -> runtime validation`.
- allowed_behavior_change:
  - Add staged medium synthesis helpers, attribution fields, medium benchmark diagnostics, tests, and review pack summary.
  - Improve medium provider prompts and batch validation/repair.
- forbidden_goal_shift:
  - No medium dedicated deterministic fast path.
  - No fixture lowering or benchmark validator weakening.
  - No agent-project/scaffold substitution.
  - No fake accepted/repaired/provider ratio.
  - No validation bypass or unbounded repair loop.
- in_scope_modules:
  - medium provider candidate pipeline.
  - live full candidate medium routing.
  - medium benchmark diagnostics/tests.
  - attribution and Review Pack evidence.
- out_of_scope_modules:
  - agent runtime/planner/web capability.
  - ordinary small-project deterministic fast paths.
  - orchestrator rewrites.
  - benchmark fixture lowering.
- completion_evidence:
  - medium benchmark pass.
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
  - `meta/reports/REVIEW_PACK.md`
  - `meta/reports/LAST.md`
  - `meta/tasks/CURRENT.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/archive/20260518-medium-provider-candidate-recovery.md`
  - `meta/reports/archive/20260518-medium-provider-candidate-recovery.md`
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

- Phase 21 failure evidence:
  - `live_provider_inventory_manager_app`: fallback.
  - `live_provider_knowledge_base_app`: fallback.
  - `provider_medium_success=false`.
- Medium provider failures were not app runtime failures; fallback projects passed runtime validation. The missing piece is a staged provider candidate that preserves enough provider-authored files and lets targeted repair fix only bounded core runtime defects.

## Plan

1. Add staged medium candidate helper functions and metadata fields.
2. Route medium project candidate generation through staged plan/batch/assembly instead of single-shot full candidate.
3. Update benchmark diagnostics and pass rules.
4. Add focused staged pipeline and batching tests.
5. Run targeted medium commands, then blind matrix, then full regression only if medium passes.

## Integration Check (before implementation)

- upstream: ordinary `new-run/status/advance` and analysis/source_generation artifacts.
- current_module: medium provider candidate staged synthesis and validation.
- downstream: project_output, generated tests, runtime validation, attribution, benchmark reports, and Review Pack.
- source_of_truth: user Phase 21B task plus active task card.
- fallback: deterministic fallback remains honest and does not count as provider medium success.
- acceptance_test: medium benchmark, blind matrix, full regression, unittest discover, workflow/module/patch/code-health checks, and verify_repo.
- forbidden_bypass: no agent-project/scaffold substitution, no medium dedicated fast path, no fixture lowering, no validation bypass.
- user_visible_effect: medium provider candidate can become accepted/repaired under validation with transparent attribution.
- Upstream connection: ordinary `new-run/status/advance` still drives analysis and source_generation; medium candidate synthesis is only a provider-assisted source-generation implementation detail.
- Downstream connection: generated project output is still validated by generated tests, HTTP/static runtime checks, SQLite persistence checks, attribution, and benchmark summaries.
- Protected integration: no agent-project/scaffold/runtime path is used for ordinary medium generation; no medium dedicated deterministic fast path is added.

## Check / Contrast / Fix Loop Evidence

- Check: Phase 21 medium benchmark previously produced only fallback outcomes, so provider medium success stayed false.
- Contrast: Phase 21B target requires staged provider plan/manifest/batch synthesis with at least one accepted/repaired medium candidate and honest fallback classification.
- Fix: add staged medium candidate pipeline, batch-level validation/retry, max-one targeted repair, expanded attribution, and Review Pack evidence.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: provider plan -> manifest -> file batches -> project_output -> validation -> attribution/report.
- accumulated: benchmark summaries, attribution JSON, Review Pack, and LAST report carry the result forward.
- consumed: tests and benchmark pass rules consume the provider candidate outcome, authored file ratio, and fallback evidence before claiming provider medium success.

## Issue Memory Decision Evidence

- no new issue-memory entry: this is a bounded provider-generation capability repair with benchmark coverage, not a new recurring user-visible runtime failure class.

## Acceptance Checks

- [x] staged medium pipeline exists.
- [x] provider plan requested and manifest validated.
- [x] file batches generated and restricted to manifest paths.
- [x] provider_project_candidate_count >= case_count when provider returns valid manifests.
- [x] accepted_count + repaired_count >= 1.
- [x] fallback_count <= 1.
- [x] failed_count == 0.
- [x] accepted/repaired provider_authored_file_ratio >= 0.6.
- [x] attribution includes plan/manifest/batch fields.
- [x] Review Pack includes Phase 21B summary.
- [x] ordinary `new-run/status/advance` preserved.
- [x] no agent-project/scaffold used.
- [x] no medium dedicated deterministic fast path added.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: gated CTCP implementation with task binding, scoped patch, benchmark evidence, and repo reporting.
