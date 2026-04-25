# Task - Agent League benchmark review layer

Archived from `meta/tasks/CURRENT.md` when switching to `ADHOC-20260423-indie-studio-hub-generation-test`.

## Queue Binding

- Queue Item: `ADHOC-20260423-agent-league-benchmark-review`
- Layer/Priority: `L1 / P1`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: `formal_basic_benchmark` and `formal_hq_benchmark` are already fixed standard regressions; the next useful layer is a post-benchmark multi-role review that can expose gray-area quality gaps and fake-success risks.
- Dependency check:
  - `formal_basic_benchmark = pass`
  - `formal_hq_benchmark = pass`
- Lane: Delivery Lane for adding a benchmark-adjacent regression/review tool.
- Scope boundary: add Agent League as a post-benchmark review layer; do not replace benchmark gates and do not repair repo-level dirty-worktree/module-protection failures.

## Task Truth Source (single source for current task)

- task_purpose:
  - implement a sequential Agent League with Customer, Product Reviewer, QA/Adversarial, and Delivery Critic roles
  - make each role consume a different artifact slice from an existing benchmark run_dir
  - emit role-level markdown reports and a unified scored summary
  - keep formal benchmark pass/fail and repo-level canonical verify separate
- allowed_behavior_change:
  - `docs/47_agent_league.md`
  - `agent_league_cases/`
  - `scripts/run_agent_league.py`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - do not change `formal_basic_benchmark` or `formal_hq_benchmark` pass criteria
  - do not rerun or redesign the benchmark mainline
  - do not repair repo-level module protection / dirty worktree in this task
  - do not make all roles read the same unrestricted input pile
- in_scope_modules:
  - deterministic role checklists
  - sequential Agent League runner
  - summary and markdown report generation
  - minimal validation against an existing benchmark run
- out_of_scope_modules:
  - project generation source logic
  - provider/API retry logic
  - formal benchmark gates
  - repo-level canonical verify repair
- completion_evidence:
  - `scripts/run_agent_league.py` compiles
  - Agent League run on an existing benchmark run_dir produces four role reports plus JSON/MD summary
  - summary includes total score, verdict, at least one real positive, and at least one real issue when present
  - `python scripts/workflow_checks.py` passes

## Results

- Added `docs/47_agent_league.md` describing purpose, roles, inputs, outputs, scoring, verdicts, and benchmark relationship.
- Added structured role rubrics under `agent_league_cases/`.
- Added `scripts/run_agent_league.py` sequential runner.
- Verified the runner on the existing formal HQ PASS run: total score `100`, verdict `PASS`, all four role reports and both summaries generated.
- Verified the runner on the existing formal basic PASS run: total score `94`, verdict `PASS`, and Product Reviewer surfaced the basic run's thinner page-depth risk.
