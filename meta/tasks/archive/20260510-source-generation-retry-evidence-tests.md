# Task Archive - Source Generation Retry Evidence Tests

## Queue Binding

- Queue Item: `ADHOC-20260510-source-generation-retry-evidence-tests`
- Layer/Priority: `L1 / P0`
- Lane: `Delivery Lane`
- Date: `2026-05-10`

## Scope

- Add regression coverage for live API source_generation retry blockers.
- Strengthen prompt evidence rendering for export probe status, signature drift, interface metadata mismatch, and missing visual evidence.
- Keep gates intact and avoid generated-source manual repair.

## Changes

- `tests/test_source_generation_prompt_leakage.py` now has a live-API-shaped regression for export/signature/visual blockers.
- `ctcp_adapters/source_generation_prompt.py` now renders probe `rc/status`, explicit export exit-0 repair guidance, and a single replacement batch retry instruction.
- `tools/providers/mock_agent.py` mock source content generation was split into helpers to repair a code-health long-function violation from the previous task.

## Command Evidence

- FIRST FAILURE: focused prompt test failed before renderer included export `rc/status` and single-batch guidance.
- PASS: focused prompt tests returned 0, 3 tests OK.
- PASS: api-agent template tests returned 0, 22 tests OK.
- PASS: mock-agent pipeline tests returned 0, 5 tests OK.
- FIRST FAILURE: code-health failed on `mock_agent.py` long-function growth.
- PASS: code-health passed after helper split.
- PASS: module protection and patch check returned 0.

## Decision

- merge_decision: merge retry evidence strengthening.
- next step: rerun bounded live API source_generation retry and compare blocker reduction.
