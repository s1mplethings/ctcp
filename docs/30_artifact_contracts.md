# Artifact Contracts (v0.2)

All files live under the external run directory unless stated otherwise.

## Verify Naming Policy (Global)

- Canonical verify artifact: `artifacts/verify_report.json`.
- `proof.json` is deprecated and non-authoritative in current CTCP contract.
- `verify_report.md` is optional human-readable material only.
- DoD pass/fail entrypoint remains `scripts/verify_repo.ps1` / `scripts/verify_repo.sh`.

## Version and Provenance Policy (Global)

- Root `VERSION` is the only authoritative repo version string.
- Any artifact that cites a version MUST record `source_version` copied from `VERSION`.
- Provenance-bearing artifacts MUST pair `source_version` with `source_commit`.
- `source_commit=unknown` is allowed only when VCS resolution is unavailable and MUST be explicit.
- Version mismatch between `VERSION`, run reports, human summaries that cite version, and generated project provenance is a metadata consistency failure.

A) artifacts/guardrails.md

Must include (simple key lines, not strict YAML):

find_mode: resolver_only | resolver_plus_web

max_files: <int>

max_total_bytes: <int>

max_iterations: <int>

If resolver_plus_web:

allow_domains: ...

max_queries: ...

max_pages: ...

B) artifacts/file_request.json (Chair -> Librarian)

Fields:

schema_version: "ctcp-file-request-v1"

goal

needs[]: { "path": "...", "mode": "full|snippets", "line_ranges": [[start,end], ...]? }

budget: { "max_files": int, "max_total_bytes": int }

reason

B.1) Librarian prompt/input contract (hard)

- The librarian execution path MUST consume `artifacts/file_request.json` before generating `artifacts/context_pack.json`.
- If `artifacts/file_request.json` is missing or unreadable, librarian MUST fail fast with an explicit error.
- Local prompt/context preparation MAY prepend repo-local contract docs and helper context, but the provider path MUST remain local-model only and MUST NOT silently fall back to remote `api_agent`.
- Chair/Planner MUST still provide budget and `needs[]` intent through `file_request.json`.

B.2) Context pack generation rules (MUST, local-model locked)

The librarian output MUST come from the hard-local-model provider path for the same run and `file_request.json`.

Path rules:
- `needs[].path` MUST be repo-relative POSIX paths (no drive letters, no `..`, no leading `/`).
- Denylist by prefix (MUST omit with `reason: denied`): `.git/`, `runs/`, `build/`, `dist/`, `node_modules/`, `__pycache__/`.
- If a path does not exist: omit with `reason: not_found`.

Provider rules:
- Default provider for `librarian/context_pack` is `ollama_agent`.
- `librarian/context_pack` is the hard-local-model role; `mode`, `role_providers`, and `CTCP_FORCE_PROVIDER` MUST NOT remap it away from `ollama_agent` (except explicit `mock_agent` test mode).
- If the local model is unavailable, returns empty content, or produces non-normalizable output, librarian MUST fail explicitly instead of pretending success.

Output rules:
- `files[].path` and `omitted[].path` MUST remain repo-relative POSIX paths.
- `omitted[].reason` MUST stay explicit (`denied|not_found|invalid_request|budget_exceeded|irrelevant|too_large|unspecified`).
- `summary` MUST describe the context-pack result without claiming downstream consumption that did not happen.

C) artifacts/context_pack.json (Librarian output)

Fields:

schema_version: "ctcp-context-pack-v1"

goal

repo_slug

summary

files[]: { "path": "...", "why": "...", "content": "..." }
files[] MAY include: { "truncated": true }

omitted[]: { "path": "...", "reason": "too_large|denied|irrelevant|not_found|invalid_request|budget_exceeded" }

Notes:
- `context_pack.json` success is valid only when the local-model provider actually returned content that normalized into this contract.
- If local-model execution fails, the run must stay failed/blocked rather than pretending `context_pack` already exists.
- `summary` MUST report high-level omitted reasons; MUST NOT include fake downstream completion claims.

D) artifacts/find_result.json (resolver final)

Fields:

schema_version: "ctcp-find-result-v1"

selected_workflow_id

selected_version

candidates[]: { "workflow_id": "...", "version": "...", "score": number, "why": "..." }

E) artifacts/find_web.json (optional, only if enabled)

Fields:

schema_version: "ctcp-find-web-v1"

constraints: { "allow_domains": [...], "max_queries": int, "max_pages": int }

results[]:

url

locator: { "type": "heading|anchor|line_range|offset", "value": "..." }

fetched_at

excerpt

why_relevant

risk_flags[]

F) artifacts/PLAN_draft.md and artifacts/PLAN.md

PLAN.md must include:

Status: SIGNED

Scope-Allow: (list of path prefixes)

Scope-Deny: (list)

Gates: (at least `lite`, `plan_check`, `patch_check`, `behavior_catalog_check`)

Stop: (stop conditions)

Budgets: (iterations/files/bytes)

Behaviors: (list of `B###` ids selected for this run)

Results: (list of `R###` ids selected for this run)

Rules:
- PLAN headers are machine-read key lines (`Key: Value`), no YAML parser required.
- `plan_check` must fail on missing required keys or unresolved Behavior/Result references.
- verify flow must record executed gates and ensure every PLAN-declared gate was executed.

F.1) artifacts/REASONS.md

Each reason line must reference at least one `B###` or `R###` id.

F.2) artifacts/EXPECTED_RESULTS.md

Each `R###` result entry must include:
- `Acceptance: ...`
- `Evidence: <path list>`
- `Related-Gates: <gate list>`

Rules:
- `plan_check --check-evidence` validates that declared Evidence paths exist.
- `patch_check` reads Scope-Allow/Scope-Deny from PLAN; missing/unparseable PLAN is a hard failure.

F.3) docs/behaviors catalog

- Index file: `docs/behaviors/INDEX.md`
- Page file: `docs/behaviors/B###-<slug>.md`
- Every behavior page must include the headings:
  - `## Reason`
  - `## Behavior`
  - `## Result`
- `behavior_catalog_check` must enforce:
  - code `BEHAVIOR_ID` marker -> INDEX entry -> page existence
  - INDEX reverse coverage (INDEX entries must have code markers and pages)

G) reviews/review_contract.md and reviews/review_cost.md

Must include:

Verdict: APPROVE|BLOCK

Blocking Reasons: (if BLOCK)

Required Fix/Artifacts: (what must be added/changed)

H) artifacts/diff.patch

unified diff, apply via git apply

must stay within PLAN scope allowlist/denylist

Patch-first enforcement (hard):

- patch must start with `diff --git`
- path normalization: repo-relative POSIX path only
- policy gate: allow_roots / deny_prefixes / deny_suffixes / max_files / max_added_lines
- `git apply --check` must pass before apply
- defaults: `max_files <= 5`, `max_added_lines <= 400`

On patch reject:

- keep candidate `artifacts/diff.patch` unchanged for evidence
- write rejection review to `reviews/review_patch.md`
- request fixer retry through outbox with "patch only" instruction

I) artifacts/verify_report.json (canonical verify artifact)

Fields:

result: "PASS"|"FAIL"

gate: "lite"|"full"

iteration: <int>

max_iterations: <int>

commands[]: { "cmd": "...", "exit_code": int }

failures[]: { "kind": "...", "id": "...", "message": "..." }

paths: {
  "trace": "TRACE.md",
  "verify_report": "artifacts/verify_report.json",
  "bundle": "failure_bundle.zip"?,
  "stdout_log": "logs/verify.stdout.log",
  "stderr_log": "logs/verify.stderr.log",
  "plan": "artifacts/PLAN.md"?,
  "patch": "artifacts/diff.patch"?
}

(compat) `artifacts` MAY mirror `paths`.

Compatibility policy:
- Legacy tools MAY emit `proof.json` or `verify_report.md` for migration,
  but gate decisions MUST rely on `artifacts/verify_report.json` (or direct verify command exit code/logs in repo-only gate runs).

J) events.jsonl

Each line:

{"ts":"...","role":"...","event":"...","path":"..."}

K) artifacts/dispatch_config.json

Fields:

schema_version: "ctcp-dispatch-config-v1"

mode: "manual_outbox" | "ollama_agent" | "api_agent" | "local_exec"

role_providers: {
  "librarian": "ollama_agent",
  "chair": "manual_outbox|api_agent",
  "contract_guardian": "manual_outbox|api_agent",
  "cost_controller": "manual_outbox",
  "patchmaker": "manual_outbox|api_agent",
  "fixer": "manual_outbox|api_agent",
  "researcher": "manual_outbox"
}

budgets: { "max_outbox_prompts": int }

Rules:
- Default path for missing `artifacts/context_pack.json` is hard-local-model librarian execution (`ollama_agent` / local Ollama).
- `librarian/context_pack` is the hard-local-model role; `mode`, `role_providers`, and `CTCP_FORCE_PROVIDER` MUST NOT remap it away from `ollama_agent` (except explicit `mock_agent` test mode).
- `ollama_agent` librarian execution MUST emit explicit local-model evidence (`provider_mode`, `model_name`, failure reason when relevant) and MUST NOT silently fall back to `api_agent`.
- `api_agent` executes configured external command templates (`SDDAI_PLAN_CMD`, `SDDAI_PATCH_CMD`, `SDDAI_AGENT_CMD`) and records stdout/stderr logs.
- For patch targets, `api_agent` output MUST start with `diff --git`, otherwise provider execution fails with explicit logs/reason.

K.1) outbox evidence pack for api_agent

Before `api_agent` execution, dispatcher MUST maintain:

- `outbox/CONTEXT.md`
- `outbox/CONSTRAINTS.md`
- `outbox/FIX_BRIEF.md`
- `outbox/EXTERNALS.md`

These files must be included in provider prompt context.

L) outbox/*.md (manual provider prompt)

Prompt must include:

Run-Dir (absolute path)

Role / Action / Target-Path

write to: <run-relative target path>

missing artifacts list

budget values (`max_outbox_prompts`, `max_files`, `max_total_bytes`, `max_iterations`)

Hard constraints:
- Only write requested target artifact in run_dir.
- Do not modify repo files.
- Follow role template output keys (for example `Verdict: APPROVE|BLOCK`, `Status: SIGNED`, patch only `artifacts/diff.patch`).
- If target is `artifacts/diff.patch`, output must be unified diff only (no prose/full-file rewrite).

M) failure_bundle.zip (on verify FAIL)

Minimum bundle content:

TRACE.md

artifacts/verify_report.json

events.jsonl

artifacts/PLAN.md (real file or placeholder entry)

artifacts/diff.patch (real file or placeholder entry)

reviews/ (directory entry) and reviews/* evidence files (when present)

outbox/ (directory entry) and outbox/* dispatch prompt/request files
reviews/review_patch.md (when patch-first gate rejects candidate patch)

Optional:

logs/**

snapshot/**

Event requirements around verify/bundle:
- `VERIFY_STARTED`
- `VERIFY_FAILED` (on non-zero verify)
- `BUNDLE_CREATED` (bundle created or validated/recreated)
- `VERIFY_PASSED` (on zero verify)

N) scaffold / scaffold-pointcloud live-reference metadata (project output + run evidence)

When `--source-mode live-reference` is used:

- Whitelist source of truth MUST be `meta/reference_export_manifest.yaml`.
- Export MUST be allowlist-only (`inherit_copy`, `inherit_transform`, `generate`, `exclude`, `required_outputs`).
- Path normalization and traversal protection are mandatory for source and target paths.

Generated project metadata:

- `meta/reference_source.json` MUST include:
  - `source_version`
  - `source_commit`
  - `source_mode`
  - `export_manifest`
  - `generated_at`
  - `profile`
  - `inherited_copy`
  - `inherited_transform`
  - `generated_files`

- Generated manifest (`manifest.json` or `meta/manifest.json` depending on scaffold type) MUST preserve/extend:
  - `files`
  - `generated`
  - `inherited_copy`
  - `inherited_transform`
  - `excluded`
  - `source_version`
  - `source_commit`
  - `source_mode`

Run evidence extension:

- Existing scaffold reports (`artifacts/scaffold_report.json`, `artifacts/scaffold_pointcloud_report.json`) MUST include:
  - `source_mode`
  - `source_version`
  - `source_commit`
  - `export_manifest_path`
  - `inherited_copy_count`
  - `inherited_transform_count`

O) test design + execution + showcase artifacts (conditional)

These artifacts are required whenever the system claims it generated tests, executed a showcase flow, or showed results to the user.

- `artifacts/test_plan.json`
  MUST include:
  - `schema_version`
  - `task_goal`
  - `source_version`
  - `source_commit`
  - `entrypoint`
  - `truth_sources`
  - `dimensions` (`normal|boundary|error|regression`)
  - `generated_at`
  - `case_count`

- `artifacts/test_cases.json`
  MUST include:
  - `schema_version`
  - `source_version`
  - `source_commit`
  - `generated_at`
  - `cases[]`
  Each case MUST include:
  - `case_id`
  - `category` (`normal|boundary|error|regression`)
  - `title`
  - `preconditions`
  - `steps[]`
  - `expected`
  - `status` (`planned|passed|failed|blocked|not_run`)
  - `actual_summary`
  - `evidence_paths[]`
  - optional `snapshot_keys[]`

- `artifacts/test_summary.md`
  MUST summarize executed scope, pass/fail counts, first failure, user-visible effect, and key evidence paths.

- `artifacts/screenshots/`
  - when visual or replay steps exist, key screenshots MUST be emitted here
  - screenshot filenames MUST be traceable to `case_id` + `step_id`, either by name or by mapping in `artifacts/test_cases.json`

- `artifacts/demo_trace.md`
  MUST narrate `did what / saw what / result was what` in user-facing order and link back to test case ids and screenshots.
  If screenshots are not available, it MUST record `screenshots_not_available_reason`.

Machine / human authority split:
- `artifacts/test_cases.json` is the canonical structured execution/result artifact.
- `artifacts/test_summary.md` and `artifacts/demo_trace.md` are human-readable derivatives and MUST not contradict `artifacts/test_cases.json`.

P) Persona Test Lab static assets and isolated run artifacts (conditional)

These artifacts are required whenever the system claims isolated style regression, persona scoring, or receptionist-tone repair evidence.

Repo-local static assets:

- `persona_lab/README.md`
  MUST describe repo-local static assets vs external run outputs.

- `persona_lab/personas/*.md`
  Each persona file MUST include:
  - `persona_id`
  - `persona_role` (`production_assistant|test_user`)
  - `language_profile`
  - `behavior_traits`
  - `common_utterances`
  - `risk_points`
  - `test_purpose`

- `persona_lab/rubrics/*.yaml`
  Each rubric MUST include:
  - `schema_version`
  - `rubric_id`
  - `purpose`
  - `authorities`
  - `checks` or `dimensions`
  - `pass_thresholds`
  - `fail_reason_templates`

- `persona_lab/cases/*.yaml`
  Each case MUST include:
  - `schema_version`
  - `case_id`
  - `purpose`
  - `assistant_persona`
  - `user_persona`
  - `initial_task` or `user_script`
  - `turn_limit`
  - `stop_conditions`
  - `must_pass_checks`
  - `fail_conditions`
  - `expected_response_traits`

External run outputs:

- Runs MUST be outside repo under:
  - `<CTCP_RUNS_ROOT>/<repo_slug>/persona_lab/<lab_run_id>/`

- Current baseline producer:
  - `scripts/ctcp_persona_lab.py`
  - scope: fixture assistant replies only
  - live production-assistant adapter remains pending and MUST NOT be implied by fixture-only artifacts

- `<lab_run_id>/manifest.json`
  MUST include:
  - `schema_version`
  - `lab_run_id`
  - `source_version`
  - `source_commit`
  - `session_policy` (`fresh_session_per_case`)
  - `production_persona`
  - `judge_rubrics`
  - `case_ids`
  - `started_at`
  - `completed_at`

- `<lab_run_id>/summary.md`
  MUST summarize:
  - executed cases
  - pass/fail counts
  - first failing case
  - score distribution
  - key fail reasons
  - evidence paths

- `<lab_run_id>/cases/<case_id>/transcript.md`
  Human-readable transcript for one isolated case.

- `<lab_run_id>/cases/<case_id>/transcript.json`
  MUST include:
  - `schema_version`
  - `case_id`
  - `session_id`
  - `assistant_persona`
  - `user_persona`
  - `language_mode`
  - `turn_limit`
  - `turns[]` (`turn_index`, `role`, `text`)
  - `stop_reason`
  - `source_version`
  - `source_commit`

- `<lab_run_id>/cases/<case_id>/score.json`
  MUST include:
  - `schema_version`
  - `case_id`
  - `judge_rubrics`
  - `check_results[]`
  - `dimension_scores`
  - `total_score`
  - `verdict` (`pass|fail`)
  - `fail_reason_ids[]`
  - `source_version`
  - `source_commit`

- `<lab_run_id>/cases/<case_id>/fail_reasons.md`
  MUST map each fail reason id to:
  - violated rule or dimension
  - offending turn reference
  - why it blocks task-progress dialogue
  - minimum repair direction

- `<lab_run_id>/cases/<case_id>/summary.md`
  MUST summarize:
  - case purpose
  - observed behavior
  - pass/fail verdict
  - next regression focus

- Optional `<lab_run_id>/cases/<case_id>/snapshots/`
  - allowed for future screenshot-capable replay or UI-linked tests
  - snapshot filenames MUST be traceable to `case_id` and step or turn id

Isolation rules:
- Each case MUST run in a fresh session and MUST NOT reuse the previous case transcript or conversation memory.
- Production conversation state and project run artifacts MUST NOT be mutated by persona-lab execution.
- Judge/scoring output is authoritative for persona-lab verdicts; human summaries MUST not contradict `score.json`.

Q) Final project output contract artifacts (project-generation tasks)

Project generation tasks MUST freeze and emit output contracts before generation:

- `artifacts/project_output_contract.json`
  - REQUIRED fields:
    - `schema_version`
    - `project_id`
    - `frozen` (must be `true` before generation)
    - `stages[]` (fixed 10-stage sequence)
    - `team_roles[]`
    - `required_interfaces[]`
    - `required_stage_artifacts.product[]`
    - `required_stage_artifacts.design[]`
    - `required_stage_artifacts.technical[]`
    - `required_stage_artifacts.qa[]`
    - `required_stage_artifacts.delivery[]`
    - `required_stage_artifacts.support_output[]`
    - `layers.source_files[]`
    - `layers.doc_files[]`
    - `layers.workflow_files[]`
    - `required_assets.images[]`
    - `required_assets.other_resources[]`
    - `acceptance_files[]`
    - `reference_project_mode` and `reference_style_applied[]`

Rules:
- `source_generation`, `docs_generation`, and `workflow_generation` are forbidden before `frozen=true`.
- Generation must preserve explicit target-layer file lists.
- Report-only completion is invalid when this contract exists.

Q.1) Team-stage run artifacts (project-generation tasks)

The run MUST keep explicit stage artifacts outside the repo under the external run directory.

Minimum artifact set:
- `artifacts/intent_brief.md`
- `artifacts/product_direction.md`
- `artifacts/architecture_decision.md`
- `artifacts/ux_flow.md`
- `artifacts/implementation_plan.md`
- `artifacts/acceptance_matrix.md`
- `artifacts/decision_log.md`
- `artifacts/qa_report.md`
- `artifacts/smoke_result.json`
- `artifacts/first_failure_stage.json` or `artifacts/first_failure_stage.md`
- delivery artifacts required by the routed contract, including screenshot/package/replay/support outputs

Rules:
- `implementation` may not start unless the product, design, and technical artifact trio exists.
- Team-stage artifacts must be goal-specific and auditable; generic fallback placeholders do not satisfy this contract.
- Content expectations for those artifacts are defined in `docs/12_virtual_team_contract.md`.

R) Project manifest contract (project-generation tasks)

Canonical manifest artifact:
- `artifacts/project_manifest.json`

REQUIRED fields:
- `schema_version`
- `project_id`
- `source_files[]`
- `doc_files[]`
- `workflow_files[]`
- `generated_files[]`
- `missing_files[]`
- `acceptance_files[]`
- `reference_project_mode`
- `reference_style_applied[]`
- `artifacts[]` (each entry includes `artifact_ref`, `path`, `kind`, `mime_type`, `readable`)

Rules:
- `missing_files[]` MUST be explicit. Empty/missing `missing_files` is not equivalent.
- Images are first-class artifacts and MUST appear in `artifacts[]` with readable metadata.
- DONE cannot be declared if `missing_files[]` is non-empty.

S) Formal output interface parity (project-generation tasks)

The following interfaces and manifest artifacts must stay consistent:
- `list_output_artifacts`
- `get_output_artifact_meta`
- `read_output_artifact`
- `get_project_manifest`

Rules:
- `list_output_artifacts` output MUST be reconcilable with `project_manifest.artifacts[]`.
- `get_output_artifact_meta` and `read_output_artifact` MUST support all key source/doc/workflow/image outputs.
- `get_project_manifest` MUST return the manifest fields defined in section R.

T) Completion and ResultEvent binding (project-generation tasks)

When publishing final result for project generation:
- Result payload MUST include explicit artifact list, not only summary text.
- Artifact list MUST include references covering source/doc/workflow layers.
- Result payload MUST surface the product/design/technical/qa/delivery stage artifact refs or a blocking missing-stage declaration.
- If reference mode is enabled, result payload MUST include mode and applied style list.
- Verify pass without artifact completeness proof is insufficient for DONE.
- Support-facing output MUST summarize completed work only; it MUST NOT claim a product/design/technical stage passed when the required artifact is missing.
- User-facing package default MUST be `final_project_bundle.zip` and it MUST contain the clean project directory plus README, screenshots, sample data, and verify summary when available.
- Internal process artifacts MUST stay separated as `process_bundle.zip` (or equivalent internal-only refs) and MUST NOT replace the final project bundle in support-facing delivery manifests.
