# Task - virtual-project-team-mainline

## Queue Binding

- Queue Item: `ADHOC-20260415-virtual-project-team-mainline`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: the user asked CTCP to stop behaving like a single coding agent and instead default to a virtual project-team flow with formal product, design, technical, QA, and delivery stages.
- Dependency check: `none required beyond the current root contract and routed docs`
- Scope boundary: docs/meta contract update only; no runtime code-path change in this patch.

## Task Truth Source (single source for current task)

- task_purpose: reframe CTCP's default purpose as a structured virtual project team rather than a single brute-force coding agent.
- task_purpose: require explicit product, design, technical, build, QA, delivery, and support-output stages for project-generation work.
- task_purpose: block generic fallback placeholders from masquerading as completed stage work.
- allowed_behavior_change:
  - `AGENTS.md`
  - `docs/01_north_star.md`
  - `docs/04_execution_flow.md`
  - `docs/03_quality_gates.md`
  - `docs/30_artifact_contracts.md`
  - `docs/41_low_capability_project_generation.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260415-virtual-project-team-mainline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260415-virtual-project-team-mainline.md`
- forbidden_goal_shift:
  - do not modify runtime code or tests in this patch
  - do not add a parallel workflow outside the existing CTCP routing model
  - do not leave the change as a one-off prompt or report-only suggestion
  - do not let design remain an informal side note outside the formal stage contract
- in_scope_modules:
  - root contract and repo purpose docs
  - execution-flow and project-generation contracts
  - artifact and quality-gate contracts
  - queue/task/report bindings for this topic
- out_of_scope_modules:
  - runtime implementation or adapter changes
  - support-style or persona-tone changes
  - unrelated delivery, replay, or SimLab repairs
- completion_evidence:
  - repo purpose and AGENTS contract both state the virtual project-team positioning
  - execution-flow and low-capability project-generation docs require explicit team stages and mandatory stage artifacts
  - quality-gate and artifact contracts explicitly block generic fallback pseudo-completion
  - workflow/doc-index checks pass and canonical contract-profile verify records the first blocking gate plus minimal fix when preexisting root plan artifacts are missing

## Analysis / Find (before plan)

- Entrypoint analysis: the authoritative behavior starts in `AGENTS.md`, then routes repo purpose to `docs/01_north_star.md`, detailed staging to `docs/04_execution_flow.md`, and project-generation completion rules to `docs/41_low_capability_project_generation.md`.
- Downstream consumer analysis: future project-generation runs, QA/delivery checks, and support-facing summaries will consume these stage rules to decide when implementation can start and when completion can be claimed.
- Source of truth:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `.agents/skills/ctcp-workflow/SKILL.md`
  - `docs/01_north_star.md`
  - `docs/04_execution_flow.md`
  - `docs/03_quality_gates.md`
  - `docs/30_artifact_contracts.md`
  - `docs/41_low_capability_project_generation.md`
  - `PATCH_README.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - user request describing the virtual project-team model and mandatory stage outputs
- Current break point / missing wiring: CTCP already has a structured mainline, but it does not yet declare product/design/technical stages as mandatory internal team outputs, and it does not yet forbid generic fallback placeholders from satisfying those stages.
- Repo-local search sufficient: `yes`

## Integration Check (before implementation)

- upstream: user goal for CTCP's default operating model plus the existing root contract and routed project-generation docs.
- current_module: repo-purpose and stage-contract documents.
- downstream: future project-generation planning, QA, delivery, and support-output decisions.
- source_of_truth: authoritative markdown contracts plus queue/task/report evidence.
- fallback: if contract-profile verify fails, record the first failing gate and make the smallest contract-doc repair only.
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile contract`
- forbidden_bypass:
  - do not claim the team-stage model is active without updating the routed contract docs
  - do not treat generic workflow/delivery artifacts as substitutes for product/design/technical outputs
  - do not broaden this contract patch into runtime implementation work
- user_visible_effect: future CTCP project work is expected to move through formal product, design, technical, implementation, QA, delivery, and support stages before it can be called complete.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: Repo purpose and the root agent contract state CTCP behaves like a structured virtual project team rather than a single brute-force coding agent
- [x] DoD-2: Expanded execution flow and low-capability project-generation contracts require explicit product, interaction design, technical planning, implementation, QA, delivery, and support-output stages with mandatory stage artifacts before build claims can stand
- [x] DoD-3: Quality-gate and artifact contracts treat missing team-stage artifacts or generic fallback pseudo-completion as blocking failures for project-generation tasks

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local scan complete)
- [x] Docs-only, no code dirs touched
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Bind a new docs-only queue item and archive the new topic in task/report indices.
2) Update the root contract and repo purpose so CTCP is explicitly positioned as a structured virtual project team.
3) Update the expanded execution flow to require product, design, technical, implementation, QA, delivery, and support-output stages.
4) Update project-generation and artifact contracts with the mandatory team-stage artifacts and no-generic-fallback rule.
5) Update quality gates so missing or generic-only stage artifacts are blocking for project-generation completion.
6) Run workflow/doc-index/contract-profile verify and record the result.
7) Completion criteria: the routed contract surface consistently reflects the team-stage model and canonical verify passes.

## Notes / Decisions

- Default choices made: keep the change contract-first and limit it to the narrowest authority files that define repo purpose, stage flow, project-generation completion, and artifact/gate semantics.
- Alternatives considered: add a new parallel team-mode document only; rejected because it would leave the default purpose and project-generation closure unchanged in the authoritative files.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: no new issue-memory entry; this is a requested contract-direction update rather than a recurring runtime failure repair.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-workflow discipline for bind -> doc-first contract change -> verify -> report.`
- persona_lab_impact: `none`, because this patch changes team-stage execution and completion contracts, not support tone, response style, or judge rubrics.

## Check / Contrast / Fix Loop Evidence

- check-1: current CTCP purpose already rejects brute-force generation, but it still lacks an explicit virtual project-team contract with formal product/design/technical stages.
- contrast-1: the requested target is a system where design is a first-class stage and implementation cannot claim readiness without upstream stage artifacts.
- fix-1: updated `AGENTS.md`, `docs/01_north_star.md`, and `docs/04_execution_flow.md` so the default purpose and stage path now name the team-style progression explicitly.
- check-2: existing project-generation completion rules require layers and artifacts, but they do not yet block generic fallback placeholders from pretending product/design/technical work is complete.
- contrast-2: the requested target is a gate-owned rule that generic workflow plans, acceptance reports, or bundles cannot impersonate stage completion.
- fix-2: updated `docs/41_low_capability_project_generation.md`, `docs/30_artifact_contracts.md`, and `docs/03_quality_gates.md` to require team-stage artifacts and make generic fallback pseudo-completion blocking.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: root contract, repo purpose, execution flow, project-generation contract, artifact contract, and quality gate all point to the same virtual project-team model
  - accumulated: the patch records the new team-stage requirements in the authoritative docs plus queue/task/report evidence
  - consumed: future CTCP runs and verify logic can use these stage requirements to reject generic fallback pseudo-completion

## Results

- Files changed:
  - `AGENTS.md`
  - `docs/01_north_star.md`
  - `docs/04_execution_flow.md`
  - `docs/03_quality_gates.md`
  - `docs/30_artifact_contracts.md`
  - `docs/41_low_capability_project_generation.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260415-virtual-project-team-mainline.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260415-virtual-project-team-mainline.md`
- Verification summary: `workflow_checks` and `sync_doc_links --check` passed; `verify_repo.ps1 -Profile contract` failed first at `plan_check` because the dirty worktree is missing root `artifacts/PLAN.md`.
- Queue status update suggestion (`todo/doing/done/blocked`): `blocked`
