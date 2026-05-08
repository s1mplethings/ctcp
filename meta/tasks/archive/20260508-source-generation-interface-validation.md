# Task Archive - Project Generation Cross-File Interface Validation

## Queue Binding

- Queue Item: `ADHOC-20260508-source-generation-interface-validation`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Code changes allowed: yes
- Lane: Delivery Lane
- Status: done

## Scope

Repair CTCP source_generation itself, not a generated project. The task added generic generated-Python cross-file signature validation and retry feedback so API-authored bundles with constructor/call drift are rejected with actionable evidence.

## Changes

- Added `tools/providers/project_generation_signature_validation.py`.
- Integrated `python_signature_consistency` into `tools/providers/project_generation_validation.py`.
- Added retry prompt consumption in `ctcp_adapters/source_generation_prompt.py`.
- Added `tests/test_generated_project_signature_validation.py`.
- Recorded issue-memory fix `20260508_003`.

## Evidence

- Focused signature validation tests: PASS, 3 tests OK.
- Existing generated-project self-repair tests: PASS, 2 tests OK.
- Project-generation artifact regression suite: PASS, 48 tests OK.
- Canonical verify: PASS with `CTCP_FORCE_PROVIDER` cleared and `CTCP_SKIP_LITE_REPLAY=1`; code profile and 523 Python tests OK, 4 skipped.

## Boundaries

- No local deterministic project template was added.
- No generated project source was manually repaired.
- No provider credentials or Telegram token files were changed.
- No domain-specific VN or voice-assistant acceptance rules were introduced.

## Skill Decision

- skillized: no, this is a validator extension inside the existing project-generation workflow, not a reusable agent workflow.
- persona_lab_impact: none.
