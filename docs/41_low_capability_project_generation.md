# Low-Capability Project Generation Contract

This contract hardens project generation for low-capability models.

Goal:
- Make it hard to output partial/ambiguous results.
- Make completion depend on complete project repository artifacts.
- Keep generation observable through formal interfaces and manifests.

Scope:
- Applies when task intent is "generate a project repository" (new or regenerated).
- Works with existing CTCP bind/read/analyze/change/verify flow in `AGENTS.md`.

Non-goals:
- Not a replacement for runtime truth ownership in `docs/00_CORE.md`.
- Not permission to copy legacy business code from reference projects.

## 1) Final Project Output Contract

Project generation output MUST be a complete project repository, not scattered files and not report-only delivery.

Minimum delivery layers:

1. Source Layer
   - runnable source entrypoint
   - dependency definition
   - configuration files
   - startup instructions (`README.md` or equivalent)
2. Documentation Layer
   - project overview
   - architecture
   - interface/API notes
   - test plan
   - acceptance criteria
   - known limits
3. Agent Workflow Layer
   - planning and analysis files
   - guardrails and shared-state boundaries
   - backend interface contract
   - queue/task/report scaffolding usable by next agents

If any required layer is missing, task is not done.

## 2) Low-Capability Fixed Stage Workflow

Project generation MUST follow one fixed stage path:

1. `intake`
2. `scope_freeze`
3. `output_contract_freeze`
4. `structure_plan`
5. `source_generation`
6. `docs_generation`
7. `workflow_generation`
8. `artifact_manifest_build`
9. `verify`
10. `deliver`

Rules:
- Each stage has one primary objective.
- Stage input/output must be explicit and saved as artifacts.
- No stage skipping.
- No cross-stage jumping.
- No code/file generation before `output_contract_freeze`.

## 3) Output Freeze Before Generation

Before generating files, system MUST freeze output contract artifacts:
- target file list
- directory skeleton
- source/doc/workflow required lists
- required interface list
- required image/resource list
- acceptance file checklist

Generation is blocked until freeze artifacts exist and pass stage self-check.

## 4) Template-Driven Generation

Project generation MUST use templates, not free-form structure invention.

Required template families:
- project output contract template
- project manifest template
- assumptions template
- acceptance checklist template
- workflow file skeleton template set

For this repository, template anchors are in `meta/templates/`.

## 5) Explicit File Lists (Mandatory)

Each generation run MUST produce all four lists:
- `target_files`
- `generated_files`
- `missing_files`
- `acceptance_files`

`missing_files` must be explicit, never implicit.
Completion cannot claim "done" when `missing_files` is non-empty.

## 6) Minimum Closed-Loop Delivery

Even under weak-model performance, the system MUST deliver a minimum closed-loop project repository:
- minimal runnable source
- baseline docs set
- baseline workflow/governance files

Advanced features may be deferred, but minimum closed-loop output cannot be skipped.

## 7) Report-Only Completion Is Forbidden

If output is only report/trace/plan without complete project files, completion is invalid.

## 8) Assumptions Management

Requirement gaps MUST be explicit:
- write `assumptions.md` or assumptions section in project docs
- mark assumption impact
- do not silently drop required files because of ambiguity

## 9) Narrow Tasks for Weak Models

Large generation goals should be decomposed into narrow subtasks, each with:
- clear input
- clear output
- clear acceptance

Final delivery MUST merge subtask outputs back into one complete project repository.

## 10) Stage Self-Check Contract

Every stage closure must record:
- stage target met or not
- missing required files
- backfill required or not
- next-stage entry allowed or blocked

If blocked, backfill first, then re-check.

## 11) Formal Output Interfaces

Completion evidence MUST be queryable through formal interfaces:
- `list_output_artifacts`
- `get_output_artifact_meta`
- `read_output_artifact`
- `get_project_manifest`

Images are first-class outputs and must be included in listing/meta/read interfaces.

## 12) Project Manifest Contract

`get_project_manifest` MUST include at minimum:
- `source_files`
- `doc_files`
- `workflow_files`
- `reference_project_mode` (enabled/disabled + mode)
- `reference_style_applied` (which structure/workflow/docs style rules were applied)
- `missing_files`
- `acceptance_files`

Manifest is required for completion, not optional telemetry.

## 13) Reference Project Mode

Reference project support is structure/process reuse only.

Modes:
- `structure_only`
- `workflow_only`
- `docs_only`
- `structure_workflow_docs` (combined style mode)

Hard boundaries:
- allowed: folder/layout/state/workflow contract style reuse
- forbidden: blind copy of unrelated historical files
- forbidden: direct carry-over of old business logic as implicit default

## 14) Hard DONE Gate (Project Generation)

All conditions below MUST be true together:

1. Source Layer generated.
2. Documentation Layer generated.
3. Agent Workflow Layer generated.
4. Key outputs enumerable via formal artifact interfaces.
5. Key outputs readable via formal artifact interfaces.
6. ResultEvent/final result includes explicit artifact list.
7. If reference mode enabled, output structure reflects declared reference style.
8. Report-only output is rejected.
9. Partial code output cannot be declared as full completion.
10. Minimum closed-loop project repository is delivered for low-capability path.

If any condition fails, status must remain non-done and `missing_files` must remain visible.
