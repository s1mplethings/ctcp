# Task - c224a08-decoupling-interface-closure

## Queue Binding

- Queue Item: `ADHOC-20260401-c224a08-decoupling-interface-closure`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context

- Baseline: `c224a08` (`3.3.2`) with user-requested boundary: no broad architecture rewrite, focus on frontend/support response quality convergence.
- This slice scope: add cross-turn near-duplicate suppression on top of unified reply policy (template_id + semantic dedupe + per-intent memory bucket + resend downgrade), and keep behavior regression-testable across fake/stub/weak-provider paths.

## Task Truth Source (single source for current task)

- task_purpose: Converge support reply behavior into a unified local policy with cross-turn dedupe memory so provider only affects wording detail, not primary behavior intent.
- allowed_behavior_change:
  - `frontend/support_reply_policy.py`
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_reply_policy_regression.py`
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260401-c224a08-decoupling-interface-closure.md`
- forbidden_goal_shift:
  - No backend/runtime refactor
  - No provider architecture rewrite
  - No unrelated business logic changes

## Analysis / Find (before plan)

- Main behavior control previously lived partly in provider output + scattered fallback blocks, and near-synonym repeats could bypass simple dedupe.
- There was no dedicated regression guard for `template_id` dedupe, semantic similarity threshold, per-intent bucket comparison, and resend downgrade behavior.
- Existing support boundary suites needed to remain green after policy convergence.

## Plan

1) Add `frontend/support_reply_policy.py` with intent-first inference, fallback rendering, and cross-turn dedupe memory gates.
2) Integrate policy+dedupe memory into `build_final_reply_doc` and session state in `scripts/ctcp_support_bot.py`.
3) Extend `tests/test_support_reply_policy_regression.py` with template/semantic/per-intent/resend-downgrade regression checks.
4) Run focused existing suites for compatibility.

## DoD Mapping (this task slice)

- [x] Reply intent is resolved before wording (`reply_intent` emitted by final reply doc).
- [x] Provider cannot decide main behavior intent (policy decides progress/decision/result/error intent).
- [x] Fallback style is centralized in one module.
- [x] Template-ID + semantic dedupe memory is active and intent-bucketed.
- [x] Resend downgrade works when same intent must be sent again.
- [x] Decision replies are explicit questions.
- [x] Result replies are artifact-first when result truth exists.
- [x] Transcript-level regression tests are present and passing.

## Results

- Files changed:
  - `frontend/support_reply_policy.py` (new)
  - `scripts/ctcp_support_bot.py`
  - `tests/test_support_reply_policy_regression.py` (new)
  - `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260401-c224a08-decoupling-interface-closure.md`
- Queue status suggestion: keep `doing` (this is a focused closure slice inside broader ADHOC item).
