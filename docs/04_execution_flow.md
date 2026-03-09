# Canonical Execution Flow (Single Flow Source)

This file is the only authoritative source for repository modification workflow.

Canonical flow:

`bind -> read -> analyze/find -> integration check -> plan -> spec -> implement -> check/fix loop -> verify -> finalize`

## Step 1: Bind

- Input: incoming request and queue context.
- Output: bound queue item in `meta/backlog/execution_queue.json` and active task card in `meta/tasks/CURRENT.md`.
- Stop condition: one explicit queue item is bound; `Queue Item: N/A` is absent.

## Step 2: Read

- Input: repository contracts.
- Output: explicit readlist in `meta/reports/LAST.md`.
- Stop condition: required contract set is recorded.

## Step 3: Analyze/Find

- Input: task request + current code/doc state.
- Output: entrypoint/downstream/source-of-truth/break-point analysis in `meta/tasks/CURRENT.md`.
- Stop condition: analysis is recorded before planning.

## Step 4: Integration Check

- Input: analysis output.
- Output: completed integration check fields in `meta/tasks/CURRENT.md` or `meta/templates/integration_check.md` instance.
- Stop condition: fields are filled: `upstream/current_module/downstream/source_of_truth/fallback/acceptance_test/forbidden_bypass/user_visible_effect`.

## Step 5: Plan

- Input: analysis + integration check.
- Output: explicit implementation plan with checks and expected fix loop.
- Stop condition: plan is recorded before implementation edits.

## Step 6: Spec

- Input: approved plan.
- Output: docs/spec/meta updates that define intended behavior and guardrails.
- Stop condition: spec/docs state reflects intended change.

## Step 7: Implement

- Input: spec-defined change scope.
- Output: minimal executable changes for the current topic only.
- Stop condition: implementation compiles/runs enough for local checks.

## Step 8: Check/Fix Loop

- Input: implementation result.
- Output: iterative `implement -> check -> contrast -> fix -> re-check` evidence.
- Stop condition: topic checks pass and triplet guard commands pass:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

## Step 9: Verify

- Input: local check/fix loop evidence.
- Output: canonical gate execution result from `scripts/verify_repo.ps1` or `scripts/verify_repo.sh`.
- Stop condition: gate passes, or first failure point and minimal fix strategy are recorded.

## Step 10: Finalize

- Input: verify outcome and artifacts.
- Output: updated `meta/reports/LAST.md`, task closure state, issue-memory decision, skill decision.
- Stop condition: completion evidence is explicit for connected + accumulated + consumed.
