# Task - project-generation-mainline-closure

Archived because the active topic moved from “manifest mainline closure” to “story business project generation mainline”.

## Queue Binding

- Queue Item: `ADHOC-20260402-project-generation-mainline-closure`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Archived Summary

- Baseline previously bound: `7777ebd2b46bcd334d14bc872bfbf184c9c93d78` / `3.2.0`
- Previous scope: dedicated project-generation workflow routing, manifest closure, and bridge readability.
- Archived reason: this scope explicitly excluded story business-code delivery and left source generation scaffold-first, which conflicts with the new `faeaedbd419aeb9de182c606cd7ce27eaa091e89` request.

## Prior Evidence Snapshot

- Workflow stages added up to `deliver`.
- `get_project_manifest` bridge exposure landed.
- Manual runner stopped injecting deliverables.

## Open Gap Handed Off

- `_default_project_file_lists(goal)` still centered on minimal scaffold files.
- `normalize_source_generation(...)` still bound to `_run_pointcloud_scaffold(...)`.
- `context_pack.json` existed but was not a required, consumed input to business code generation.
