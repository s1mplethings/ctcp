# Execution Flow (Expanded Reference)

`AGENTS.md` is the root agent contract and the first file an agent should use.
This document expands the root 5-step flow into the repository's detailed sequencing, supporting chains, and verification-profile behavior.

Root agent flow:

`bind -> read -> analyze -> change -> verify/close`

Expanded repository flow:

`bind -> read -> analyze/find -> integration check -> plan -> spec -> implement -> check/fix loop -> verify -> finalize`

Formal work-lane split:

- `Delivery Lane`
  - use for bounded implementation, repair, or direct delivery work
- `Virtual Team Lane`
  - use for new-project, open-ended, self-design, or design-heavy work
  - authority: `docs/12_virtual_team_contract.md`

Rules:
- lane selection must be recorded before implementation work starts
- if `Virtual Team Lane` is selected, required design artifacts must exist before implementation

Expanded mapping from the root flow:

- `Bind` -> Step 1
- `Read` -> Step 2
- `Analyze` -> Steps 3–5
- `Change` -> Steps 6–8
- `Verify/Close` -> Steps 9–10

Supporting chains (mandatory when relevant):

- dialogue chain: bind task state -> choose message purpose -> lint -> emit user-visible reply
- test showcase chain: generate test plan -> generate test cases -> execute -> capture snapshots -> summarize -> demo trace
- persona regression chain: select production persona -> select test user persona -> start fresh session -> run fixed turns -> judge -> record transcript/score/fail reasons
- metadata chain: `VERSION` -> report provenance -> generated output provenance

## Step 1: Bind

- Input: incoming request and queue context.
- Output: bound queue item in `meta/backlog/execution_queue.json` and active task card in `meta/tasks/CURRENT.md`.
- Stop condition: one explicit queue item is bound; `Queue Item: N/A` is absent; allowed write paths / protected paths / frozen-kernel elevation fields are filled.

## Step 2: Read

- Input: repository contracts.
- Output: explicit readlist in `meta/reports/LAST.md`.
- Stop condition: required contract set is recorded.

## Step 3: Analyze/Find

- Input: task request + current code/doc state.
- Output: entrypoint/downstream/source-of-truth/break-point analysis, plus dialogue/showcase/persona-lab/metadata impact notes, in `meta/tasks/CURRENT.md`.
- Stop condition: analysis is recorded before planning.

## Step 4: Integration Check

- Input: analysis output.
- Output: completed integration check fields in `meta/tasks/CURRENT.md` or `meta/templates/integration_check.md` instance.
- Stop condition: fields are filled: `upstream/current_module/downstream/source_of_truth/fallback/acceptance_test/forbidden_bypass/user_visible_effect`.

## Step 5: Plan

- Input: analysis + integration check.
- Output: explicit implementation plan with checks, expected fix loop, and any required response-lint / persona-lab / showcase / metadata-consistency checks.
- Stop condition: plan is recorded before implementation edits.

### Project Generation Fixed Subflow (Virtual Team Path)

When the task goal is project generation, Step 5 MUST freeze and enforce the following subflow:

1. `intake`
2. `product_brief`
3. `interaction_design`
4. `technical_plan`
5. `output_contract_freeze`
6. `implementation`
7. `qa`
8. `delivery`
9. `support_output`
10. `verify_close`

Hard rules for this subflow:
- Stage order is fixed; no jump/skip.
- Each stage must record explicit input/output and self-check result.
- `product_brief`, `interaction_design`, and `technical_plan` must all complete before `implementation`.
- `output_contract_freeze` must complete before any generated source/docs/workflow file writes.
- `output_contract_freeze` must lock `project_domain`, `scaffold_family`, and delivery shape before implementation; incompatible family fallback is a hard block, not a silent downgrade.
- Generic fallback material must not be accepted as stage completion for product/design/technical/qa/delivery.
- QA/delivery must validate domain capability, contamination, README quality, and user-facing bundle split, not only runnable entrypoints.
- Completion is blocked unless the stage artifacts, manifest build, and missing-file visibility all agree.
- the concrete design-artifact contract is owned by `docs/12_virtual_team_contract.md`

## Step 6: Spec

- Input: approved plan.
- Output: docs/spec/meta updates that define intended behavior, user-visible guardrails, required stage artifacts, and provenance rules.
- Stop condition: spec/docs state reflects intended change.

## Step 7: Implement

- Input: spec-defined change scope.
- Output: minimal executable changes for the current topic only.
- Stop condition: implementation compiles/runs enough for local checks.

## Step 8: Check/Fix Loop

- Input: implementation result.
- Output: iterative `implement -> check -> contrast -> fix -> re-check` evidence.
- Stop condition: topic checks pass, response/persona-lab/showcase/metadata checks pass when applicable, and triplet guard commands pass or are explicitly profile-skipped:
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`

## Step 9: Verify

- Input: local check/fix loop evidence.
- Output: canonical gate execution result from `scripts/verify_repo.ps1` or `scripts/verify_repo.sh`.
- Stop condition: gate passes, or first failure point and minimal fix strategy are recorded.

### Verification Profiles

`verify_repo.*` supports risk-tiered profiles to match verification effort to change scope.

Usage:
- Windows: `scripts/verify_repo.ps1 -Profile doc-only`
- Unix: `scripts/verify_repo.sh --profile doc-only`
- Env: `CTCP_VERIFY_PROFILE=doc-only`
- Auto: when no profile is specified, `scripts/classify_change_profile.py` infers it from changed files.

Profiles:
- `doc-only`: for markdown/docs/index/meta/report/archive/cleanup changes that do not affect code paths. Skips heavyweight gates (build, triplet guard, lite replay, unit tests). Runs workflow evidence, plan/patch checks, doc index, and contract checks (advisory).
- `contract`: for authoritative governance/workflow/runtime contract sources. Stricter than `doc-only`; includes behavior catalog checks. Still skips code-only gates.
- `code`: for any code/integration/script/runtime/test/build change. Full current behavior; no gates skipped.

Ownership overlay:
- `scripts/classify_change_profile.py` also classifies ownership as `task-owned`, `lane-owned`, or `frozen-kernel` using `contracts/module_freeze.json` plus `meta/tasks/CURRENT.md`.
- `lane-owned` changes add lane regression even when the type profile is `doc-only` or `contract`.
- `frozen-kernel` changes require explicit elevation in `meta/tasks/CURRENT.md`; without that signal, verify fails before claiming completion.

The expanded 10-step sequence remains the detailed workflow reference regardless of profile.
Agents should still enter through the root 5-step flow in `AGENTS.md`.
`meta/tasks/CURRENT.md` and `meta/reports/LAST.md` remain required across all profiles.

## Step 10: Finalize

- Input: verify outcome and artifacts.
- Output: updated `meta/reports/LAST.md`, task closure state, issue-memory decision, skill decision, any final persona-lab / showcase / provenance closure, and a support-facing summary that reports team results instead of inventing missing stage work.
- Stop condition: completion evidence is explicit for connected + accumulated + consumed.
