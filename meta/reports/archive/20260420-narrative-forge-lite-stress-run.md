# Demo Report - Narrative Forge Lite Stress Run

Archived from `meta/reports/LAST.md` on 2026-04-20 when the active topic moved to narrative/editor depth hardening.

## Summary

- Real run:
  - `run_id = narrative-forge-lite-stress-20260420`
  - `run_dir = D:\ctcp_runs\ctcp\narrative-forge-lite-stress-20260420`
- Routing and gates:
  - `project_domain = narrative_vn_editor`
  - `scaffold_family = narrative_gui_editor`
  - `allowed_families = ["narrative_gui_editor"]`
  - `incompatible_families = ["pointcloud_reconstruction"]`
  - `domain_compatibility.passed = true`
  - `domain_validation.passed = true`
  - `contamination_hits = []`
- Delivery:
  - `final_project_bundle.zip` exists and is the selected user-facing document
  - `process_bundle.zip` exists and is retained as the internal artifact
- README/meta quality:
  - `readme_quality.passed = true`
  - `goal_dump_detected = false`
  - `escaped_literal_hits = []`

## Remaining Gap Handed Off

- The generated narrative/editor family output was type-correct but still shallow:
  - sample content depth below the requested threshold
  - UX evidence still looked too close to an export-backed summary page
  - no explicit provenance/source-map artifact for narrative sample content
