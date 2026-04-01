# Project Generation Acceptance Checklist

- [ ] `intake` completed
- [ ] `scope_freeze` completed
- [ ] `output_contract_freeze` completed before any generation
- [ ] `structure_plan` completed
- [ ] `source_generation` completed
- [ ] `docs_generation` completed
- [ ] `workflow_generation` completed
- [ ] `artifact_manifest_build` completed
- [ ] `verify` completed
- [ ] `deliver` completed

## Layer Completion

- [ ] Source Layer complete
- [ ] Documentation Layer complete
- [ ] Agent Workflow Layer complete

## Artifact Interface Completion

- [ ] `list_output_artifacts` works for key outputs
- [ ] `get_output_artifact_meta` works for key outputs
- [ ] `read_output_artifact` works for key outputs
- [ ] `get_project_manifest` returns required fields
- [ ] images are included in artifact interfaces

## Explicit Lists

- [ ] `target_files` declared
- [ ] `generated_files` declared
- [ ] `missing_files` declared
- [ ] `acceptance_files` declared

## Done Gate

- [ ] ResultEvent includes explicit artifact list
- [ ] reference mode style rules are reflected when enabled
- [ ] report-only output is rejected
- [ ] minimum closed-loop project repository is delivered
