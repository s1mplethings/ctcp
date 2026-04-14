# Task - cold-delivery-replay-gate

## Queue Binding

- Queue Item: `ADHOC-20260413-cold-delivery-replay-gate`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now: verify plus package plus delivery already exist, but CTCP still lacks a cold package replay gate that proves the delivered output can restart outside the original run.
- Dependency check: `ADHOC-20260412-spec-delivery-repair-loop = doing`
- Scope boundary: add one post-delivery anti-hallucination replay validator and wire it into the existing completion path without broad refactors.

## Task Truth Source (single source for current task)

- task_purpose:
  - add a repeatable cold replay validator that only needs the final package and in-package startup hints
  - persist `replay_report.json` and a replay screenshot for the delivered package
  - fold cold replay pass into the existing delivery/completion authority path
  - keep verify, virtual delivery, and production manual/Telegram defaults intact
- allowed_behavior_change:
  - `scripts/support_public_delivery.py`
  - `scripts/delivery_replay_validator.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/ctcp_orchestrate.py`
  - focused replay/delivery tests
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- forbidden_goal_shift:
  - do not let `verify pass` alone represent completion
  - do not accept manifest text without a real package replay result
  - do not depend on the original run directory cache or a live network
  - do not introduce a second competing success definition
- in_scope_modules:
  - package replay runner
  - delivery completion gate
  - verify-pass delivery closure
  - replay-focused tests and verify wiring
- out_of_scope_modules:
  - spec/planning/front-half repairs
  - broad UI or support copy changes
  - unrelated architecture cleanup
- completion_evidence:
  - replay success/failure tests exist
  - virtual delivery E2E still passes
  - SimLab lite passes
  - canonical verify passes

## Analysis / Find (before plan)

- Entrypoint analysis: `scripts/support_public_delivery.py` already owns offline delivery closure and is the narrowest place to add replay after package+manifest materialize.
- Downstream consumer analysis: `frontend/delivery_reply_actions.py::evaluate_delivery_completion` is the single reusable delivery success gate consumed by support flows and tests.
- Source of truth:
  - `AGENTS.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `scripts/support_public_delivery.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/ctcp_orchestrate.py`
  - `tests/support_virtual_delivery_e2e_runner.py`
- Current break point / missing wiring: successful runs can already leave a zip and valid delivery manifest, but nothing proves the shipped zip can cold-start and regenerate a runnable artifact in a fresh directory.
- Repo-local search sufficient: `yes`
- If no, external research artifact: `meta/externals/YYYYMMDD-<topic>.md`

## Integration Check (before implementation)

- upstream:
  - `scripts/ctcp_support_bot.py::emit_public_delivery`
  - `tests/support_virtual_delivery_e2e_runner.py`
- current_module:
  - `scripts/support_public_delivery.py`
  - `frontend/delivery_reply_actions.py`
  - `scripts/ctcp_orchestrate.py`
- downstream:
  - `artifacts/support_public_delivery.json`
  - `artifacts/replay_report.json`
  - verify-pass run closure and replay-focused regressions
- source_of_truth:
  - `frontend/delivery_reply_actions.py::evaluate_delivery_completion`
  - `tools/providers/project_generation_source_helpers.py`
- fallback:
  - if a replay step cannot infer an entrypoint, fail with an explicit first failure stage instead of synthetic success
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python -m unittest discover -s tests -p "test_delivery_replay_validator.py" -v`
  - `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json`
  - `python simlab/run.py --suite lite`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code`
- forbidden_bypass:
  - do not score replay success from existing screenshots in the original run
  - do not rely on agent prose instead of a real extracted package replay
  - do not weaken package/delivery checks to offset replay failures
- user_visible_effect:
  - a run only counts as truly delivered when its final zip can be unpacked elsewhere, restarted, and produce fresh replay evidence.

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: A repeatable cold replay validator exists that only needs the final package plus in-package startup hints, extracts into a fresh temp dir, and writes replay_report.json plus a replay screenshot
- [ ] DoD-2: The delivery/completion success definition now requires verify pass, package pass, delivery pass, and cold replay pass through one authority path instead of parallel success rules
- [ ] DoD-3: Focused replay success/failure tests, virtual delivery E2E, simlab lite, and canonical verify all pass without adding network or human steps

## Acceptance (must be checkable)

- [x] DoD written (this file complete)
- [x] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [x] Code changes allowed (or explicitly "Docs-only, no code dirs touched")
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Rebind the task and clear workflow precheck before touching code.
2) Add a small standalone replay validator that accepts a package zip and writes `replay_report.json`.
3) Add focused replay failure/success tests and use them immediately after the new helper lands.
4) Extend the existing delivery completion gate so replay becomes part of the single authority path.
5) Wire replay into the verify-pass auto-delivery closure.
6) Rerun virtual delivery E2E and targeted delivery/orchestrate regressions.
7) `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
8) `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
9) `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
10) Record the first failure and minimal fix strategy, then run canonical verify and prove `connected + accumulated + consumed`.

## Check / Contrast / Fix Loop Evidence

- check-1: current completion can stop at `verify pass + package + delivery manifest`, so a non-runnable package can still appear complete.
- contrast-1: a real delivery should prove the shipped zip can re-enter from a clean directory using only its own startup hints.
- fix-1: add a cold replay validator that extracts the package, detects an entrypoint, runs a minimal startup/export path, and writes `replay_report.json`.
- check-2: delivery success is already centralized in `evaluate_delivery_completion`, so putting replay elsewhere would create competing truth.
- contrast-2: replay must become part of the same completion authority instead of a sidecar note.
- fix-2: extend the current completion gate with replay evidence and invoke replay from the existing verify-pass auto-close hook.

## Notes / Decisions

- Default choices made: prefer using the delivered zip plus package contents as the only replay input, and generate new replay evidence under the extracted package temp root.
- Alternatives considered: checking only README/manifest text; rejected because it would not prove the package can really restart in a clean directory.
- Any contract exception reference (must also log in `ai_context/decision_log.md`):
  - None
- Issue memory decision: if replay fails after delivery closure, record the first replay stage and keep it as the new downstream blocker instead of burying it under generic verify success.
- Skill decision (`skillized: yes` or `skillized: no, because ...`): `skillized: yes, using ctcp-gate-precheck for pre-change task/gate validation before the first code edit.`

## Results

- Files changed:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
- Verification summary: pending implementation
- Queue status update suggestion (`todo/doing/done/blocked`): `doing`
