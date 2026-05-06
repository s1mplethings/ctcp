# Task Archive - API Source Runnability Tightening

- Date: `2026-05-03`
- Queue Item: `ADHOC-20260503-api-source-runnability-tightening`
- Lane: Delivery Lane
- Status: done

## Scope

Make API-authored source output more likely to become a visible runnable project by tightening prompt requirements and preserving provider source-map provenance.

## Changes

- `ctcp_adapters/source_generation_prompt.py` now requires all contract file groups and local runtime behavior.
- Prompt explicitly avoids undeclared GUI dependencies such as PyQt5 and prefers stdlib/tkinter for local GUI output.
- `tools/providers/project_generation_source_stage.py` merges provider source-map content and augments sparse maps with API refs.
- Regressions cover prompt requirements and source-map preservation.

## Verification

- Focused prompt/provenance/project-generation tests passed.
- `workflow_checks.py` passed.
- Current-task `code_health_check.py` passed.
- Canonical verify is blocked at module protection by unrelated dirty lane files outside this task scope.
