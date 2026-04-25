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
- Not permission to treat any fixed narrative benchmark sample as the production default project target.

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

Project-queue extension:
- When the incoming request is explicitly a queue of multiple rough-goal projects, generation MAY keep one top-level runnable portfolio root as the gate-visible project output.
- That portfolio root MUST still contain per-project independent subdirectories with their own intake/freeze/design/build/verify/delivery artifacts, strongest-available bundles, and verdict fields.
- A portfolio-root shortcut is valid only when it preserves independent project evidence; it must not collapse multiple queued projects into one generic bundle or one generic report.

### 1.1) Production Mode vs Benchmark / Regression Mode

Project generation MUST separate real-user production work from fixed-sample benchmark work.

Production mode:
- applies to real user requests
- MUST classify project type before workflow/agent selection
- MUST decide `gui-first|cli-first|web-first|tool-first` from project type and user goal
- demo, screenshots, visual verification, export contract, and deliverable shape MUST follow project type and user goal
- MUST NOT hard-code benchmark story, roles, chapters, export names, or demo payloads into default output contracts

Benchmark / regression mode:
- applies to fixed-sample replay for mainline, gate, deliverable, and evidence-chain validation
- MAY use a fixed narrative benchmark sample such as `Mystery Narrative Copilot` / `镜廊疑影` as a benchmark case
- MUST NOT use benchmark output to define production default project content
- MUST NOT let benchmark sample content overwrite or pollute a real user request

### 1.2) Project-Type Decision Before Generation

Real project generation MUST follow this decision order:
- generic project intake
- project type classification
- workflow/agent decision
- generation
- manifest/deliver
- verify/gates
- regression replay when required

Rules:
- Real requests MUST NOT directly inherit a narrative benchmark sample just because that sample exists in regression.
- Real requests MUST bind a compatible `project_domain -> scaffold_family` pair before generation; narrative / VN / GUI editor requests MUST NOT fall through to pointcloud / v2p / reconstruction families.
- Agent MUST decide whether GUI, CLI, web flows, demo assets, screenshots, state persistence, or export support are required from project type and user goal.
- GUI is not a default mandatory path.
- CLI is not a default downgrade path.
- Benchmark samples are validation inputs only, not production defaults.

## 2) Low-Capability Fixed Stage Workflow

Project generation MUST follow one fixed stage path:

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

Rules:
- Each stage has one primary objective.
- Stage input/output must be explicit and saved as artifacts.
- No stage skipping.
- No cross-stage jumping.
- No code/file generation before `output_contract_freeze`.
- `implementation` is blocked until `product_brief`, `interaction_design`, and `technical_plan` are all present and approved for the current goal.

### 2.1) Fixed Virtual Team Roles

Project generation MUST behave like a fixed internal team, even when one runtime path executes the work.

Required role lanes:
- Product Manager
- UX / Interaction Designer
- Tech Lead
- Builder / Engineer
- QA
- Delivery / Support

The runtime MAY consolidate execution, but it MUST NOT skip the role-owned stage outputs.

### 2.2) Mandatory Stage Artifacts

Before completion, the run MUST emit all of the following stage artifacts:

1. Product stage
   - `intent_brief.md`
   - `product_direction.md`
   - `decision_log.md`
2. Design stage
   - `ux_flow.md`
3. Technical stage
   - `architecture_decision.md`
   - `implementation_plan.md`
4. Build stage
   - runnable project output
   - core feature implementation
   - minimum main user path
5. QA stage
   - `acceptance_matrix.md`
   - `qa_report`
   - `smoke_result`
   - `first_failure_stage`
6. Delivery stage
   - high-value screenshot
   - package artifact
   - startup README
   - `support_public_delivery.json`
   - `replay_report.json`
   - `replayed_screenshot.png`

Rules:
- The support/output stage may summarize results to the user, but it MUST NOT invent missing product/design/technical work.
- Generic fallback material such as a generic workflow plan, generic acceptance report, or generic project bundle MUST NOT satisfy any of the required stage artifacts.
- Narrative / VN / GUI editor completion MUST prove editor/authoring capability, narrative structure, asset/cast structure, sample project data, and preview/export evidence; export-only shells are insufficient.
- Incompatible family contamination (for example pointcloud / v2p scripts or tests inside narrative/editor output) is a blocking failure, not a warning.
- `docs/12_virtual_team_contract.md` is the authority for what those artifacts must contain.

## 3) Output Freeze Before Generation

Before generating files, system MUST freeze output contract artifacts:
- target file list
- directory skeleton
- source/doc/workflow required lists
- required interface list
- required image/resource list
- acceptance file checklist

Generation is blocked until freeze artifacts exist and pass stage self-check.

### 3.1) Effective `context_pack` Consumption

`context_pack.json` presence alone is not effective consumption.

`context_pack` counts as consumed only when it has provable impact on at least one of:
- project type classification
- generation strategy or workflow/agent choice
- output contract / deliverable contract
- business/module selection

If `context_pack` exists but none of the above changes can be shown in artifacts or reports, consumption is incomplete.

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
The minimum closed-loop shape MUST still be derived from project type and user goal, not from any fixed narrative benchmark sample.
The user-facing delivery package for this closed loop MUST be a clean final project bundle, not the internal process/run bundle.

## 7) Report-Only Completion Is Forbidden

If output is only report/trace/plan without complete project files, completion is invalid.
If output includes only generic fallback stage documents without goal-specific product/design/technical substance, completion is also invalid.

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

### 10.1) Gate Layering

Project-generation gates MUST distinguish these layers:
- structural completion: required files, entrypoints, manifest, and deliverable inventory exist
- behavioral completion: the project can start, execute its main flow, and export or deliver what the contract says it should
- result completion: the result matches the real user request, or matches the declared benchmark sample when running benchmark / regression mode

Rules:
- Passing structural gates does not prove full project delivery.
- Passing implementation, QA, delivery, or replay gates does not retroactively excuse missing product/design/technical stages.
- Production-mode result gates and benchmark-mode result gates MUST NOT be mixed.
- A fixed narrative benchmark may satisfy benchmark-result checks only; it does not define production completeness.

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

### 13.1) Benchmark Sample Boundary

Testing rules are a separate concern from production defaults.

Rules:
- Fixed narrative benchmark samples belong to benchmark / regression rules only.
- Fixed benchmark characters, chapter names, export names, screenshots, and demo content are valid only for benchmark acceptance.
- Those benchmark details MUST NOT be written into production default output contracts, manifest defaults, or delivery templates.

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
11. Required product/design/technical/qa/delivery artifacts exist and are not generic-fallback placeholders.
12. Support output only summarizes completed team stages; it does not mask missing stages.

If any condition fails, status must remain non-done and `missing_files` must remain visible.
