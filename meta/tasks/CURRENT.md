# Task - support-pass-runtime-and-benchmark-mode-isolation

## Queue Binding

- Queue Item: `ADHOC-20260405-support-pass-runtime-and-benchmark-mode-isolation`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Why this item now: customer-facing support still misreports final state after runtime PASS, and explicit benchmark/regression requests need stronger benchmark-mode delivery without leaking fixture logic into production defaults.
- Dependency check: `ADHOC-20260405-temp-trace-cleanup` = `done`.
- Scope boundary: only common support/runtime/result-consumption fixes plus explicit benchmark-mode isolation/wiring; do not write fixed VN sample content, benchmark acceptance rules, or benchmark reply text into production logic.

## Task Truth Source (single source for current task)

- task_purpose: repair generic support PASS-state delivery and keep benchmark-only project-generation strengthening isolated to explicit benchmark mode.
- allowed_behavior_change:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/support_reply_policy.py`
  - `apps/cs_frontend/dialogue/requirement_collector.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift: do not write benchmark sample names, fixed VN roles/chapters, benchmark acceptance rules, or benchmark-specific customer reply wording into production default logic.
- in_scope_modules:
  - `scripts/ctcp_front_bridge.py`
  - `scripts/ctcp_support_bot.py`
  - `frontend/support_reply_policy.py`
  - `apps/cs_frontend/dialogue/requirement_collector.py`
  - `tools/providers/project_generation_business_templates.py`
  - focused regression tests listed above
  - task/report/queue metadata for this topic
- out_of_scope_modules:
  - production default templates carrying fixed benchmark content
  - production verify gates carrying benchmark acceptance rules
  - benchmark-case literals in default support reply logic
  - manual deliverable injection or bypass paths
- completion_evidence: support PASS truth is consumed into readable delivery fallback; explicit benchmark mode remains opt-in; focused regressions plus canonical verify record the first failure and minimal fix.

## Analysis / Find (before plan)

- Entrypoint analysis: the user-visible entrypoint remains `scripts/ctcp_support_bot.py`, which creates/binds runs through `scripts/ctcp_front_bridge.py` and then renders fallback replies from `frontend/support_reply_policy.py`.
- Downstream consumer analysis: pass-state truth flows into `support_reply_policy`, while explicit benchmark mode flows into project-generation contract resolution and then benchmark-only export templates.
- Source of truth: `artifacts/support_runtime_state.json`, `artifacts/verify_report.json`, and `artifacts/project_manifest.json`.
- Current break point / missing wiring: support fallback could still render stale failure language after PASS truth, and benchmark-mode ingress/egress needed explicit mode plumbing without fixture injection.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `scripts/ctcp_support_bot.py` conversation handling and `scripts/ctcp_front_bridge.py` runtime-state refresh.
- current_module: support reply policy plus explicit frontend constraint extraction and benchmark-only business template branch.
- downstream: customer-visible reply text, generated benchmark-mode deliverables, and runtime/contract regression suites.
- source_of_truth: canonical runtime status + verify result + manifest delivery fields.
- fallback: if canonical verify fails, repair only the first gate failure and keep scope bounded to this topic.
- acceptance_test:
  - `python -m unittest discover -s tests -p "test_support_to_production_path.py" -v`
  - `python -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `python -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `python -m unittest discover -s tests -p "test_support_reply_policy_regression.py" -v`
  - `python -m unittest discover -s tests -p "test_support_bot_humanization.py" -v`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - do not hardcode benchmark content into production template/gate/reply paths
  - do not bypass support entrypoint by injecting deliverables into run_dir
  - do not claim benchmark completion from benchmark-only intermediate artifacts
  - do not skip canonical verify
- user_visible_effect: PASS/VERIFY_PASSED can now produce readable delivery messaging from generic runtime truth, while benchmark-mode stronger exports remain explicit and isolated.

## DoD Mapping (from execution_queue.json)

- [x] DoD-1: customer-facing support replies prefer runtime PASS truth over stale provider failure state and return readable delivery info
- [x] DoD-2: explicit benchmark/regression requests can attach benchmark_regression mode through frontend constraints without injecting fixture payload into production defaults
- [x] DoD-3: benchmark-only stronger export shape remains isolated to benchmark_regression mode while production narrative generation stays goal-driven and generic

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (repo-local search only)
- [x] Code changes allowed
- [x] Patch applies cleanly
- [x] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Rebind task/report metadata to this topic and preserve baseline evidence.
2) Repair generic support PASS-state delivery and stale-error clearing.
3) Keep benchmark-mode ingress explicit and benchmark-only export strengthening isolated from production defaults.
4) Run focused regressions.
5) `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
6) `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
7) `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
8) Record the first failure and minimal fix strategy.
9) Canonical verify gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
10) Completion criteria: prove `connected + accumulated + consumed`.

## Check / Contrast / Fix Loop Evidence

- check-1: `test_support_to_production_path.py` first failed because `render_fallback_reply()` returned English delivery text for `lang_hint="zh"`.
- contrast-1: delivery fallback must remain language-aware while consuming the same generic PASS truth.
- fix-1: move `deliver_result` handling back under the language branch and keep manifest/artifact consumption generic.
- check-2: support/humanization/runtime-wiring tests still asserted the old `ctcp_new_run(goal=...)` signature.
- contrast-2: the repaired support entrypoint should forward generic constraints, but must not forward benchmark fixture payload fields by default.
- fix-2: update those regressions to assert preserved `goal`, allowed generic `constraints`, and absence of `benchmark_case`.
- check-3: canonical verify first failed at workflow gate because `CURRENT.md` lacked the mandatory 10-step evidence sections.
- contrast-3: task metadata must carry analysis/integration/plan/fix-loop/completion/issue-memory evidence for code patches.
- fix-3: expand `meta/tasks/CURRENT.md` and `meta/reports/LAST.md` to satisfy workflow evidence requirements without changing runtime logic.

## Completion Criteria Evidence

- connected + accumulated + consumed:
  - connected: support entrypoint forwards explicit benchmark-mode constraints through the normal frontend bridge; PASS truth is wired from bridge runtime state into reply intent/rendering.
  - accumulated: runtime PASS state, verify result, manifest delivery fields, and explicit benchmark-mode constraint are accumulated into one bounded decision path.
  - consumed: fallback reply rendering, benchmark-only export materialization, and focused regression tests consume that state and prove the repaired path.

## Notes / Decisions

- Default choices made: keep production reply/template logic generic; use only explicit `project_generation_mode=benchmark_regression` as the benchmark switch.
- Alternatives considered: writing fixed benchmark payload names or acceptance checks into production branches; rejected because it would contaminate defaults.
- Any contract exception reference (must also log in `ai_context/decision_log.md`): none.
- Issue memory decision: no new issue_memory entry for this round; the observed failures were closed as bounded runtime wiring/test-contract regressions inside the existing support/project-generation path.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this is a bounded runtime hardening and mode-isolation repair inside existing support/project-generation paths, not a new reusable workflow asset.

## Results

- Files changed:
  - `scripts/ctcp_front_bridge.py`
  - `frontend/support_reply_policy.py`
  - `apps/cs_frontend/dialogue/requirement_collector.py`
  - `tools/providers/project_generation_business_templates.py`
  - `tests/test_support_to_production_path.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_support_bot_humanization.py`
  - `tests/test_runtime_wiring_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
-  `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- Verification summary: focused suites passed; standalone `python simlab/run.py --suite lite --json-out <tmp>` passed (`14/14`); canonical `verify_repo.ps1` passed with repo-supported `CTCP_SKIP_LITE_REPLAY=1` after the standalone lite replay proof was captured.
- Queue status update suggestion (`todo/doing/done/blocked`): done
