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

B.1) Librarian mandatory contract injection (hard)

- `scripts/ctcp_librarian.py` MUST prepend mandatory contract docs before processing `needs[]`:
  - `AGENTS.md`
  - `ai_context/00_AI_CONTRACT.md`
  - `ai_context/CTCP_FAST_RULES.md` (single-screen hard-rule summary for fast policy injection)
  - `docs/00_CORE.md` (if present)
  - `PATCH_README.md` (if present)
- Duplicate paths MUST be de-duplicated (mandatory copy wins).
- Mandatory docs consume budget first.
- If `budget.max_files` or `budget.max_total_bytes` cannot cover mandatory docs, librarian MUST fail with a clear "increase budget" error.
- Chair/Planner MUST reserve budget for mandatory docs before adding extra `needs[]`.

B.2) Context pack generation rules (MUST, deterministic)

The librarian output MUST be deterministic for the same `(repo, file_request.json)`.

Path rules:
- `needs[].path` MUST be repo-relative POSIX paths (no drive letters, no `..`, no leading `/`).
- Denylist by prefix (MUST omit with `reason: denied`): `.git/`, `runs/`, `build/`, `dist/`, `node_modules/`, `__pycache__/`.
- If a path does not exist: omit with `reason: not_found`.

Mode rules:
- `mode="full"`: include verbatim file bytes as UTF-8 (replacement allowed) and MAY truncate to fit budget.
- `mode="snippets"`: include only requested line ranges.
- `line_ranges` are 1-indexed inclusive `[start,end]`.
- If `mode="snippets"` and `line_ranges` is missing/empty: omit with `reason: invalid_request`.
- Out-of-range line ranges MUST be clamped deterministically to file bounds.

Budget rules:
- Apply B.1 mandatory injection first.
- Then process `needs[]` in order.
- When the next file/snippet would exceed `budget.max_files` or `budget.max_total_bytes`, omit with `reason: budget_exceeded`.

Truncation:
- For `mode="full"` when remaining budget is smaller than file size, include prefix that fits and mark `truncated: true`.

Verbatim-only rule:
- `files[].content` MUST be copied from repo files; librarian MUST NOT invent/summarize/paraphrase.
- `files[].why` MUST be short provenance text (for example `mandatory_contract`, `requested:<reason>`).

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
- `files[]` MUST include the mandatory contract docs listed in B.1 when budget is sufficient.
- If mandatory docs cannot fit, context generation MUST fail instead of silently omitting them.
- `summary` MUST report high-level omitted reasons; MUST NOT include plans/solutions.

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
  "librarian": "local_exec",
  "chair": "manual_outbox|api_agent",
  "contract_guardian": "local_exec",
  "cost_controller": "manual_outbox",
  "patchmaker": "manual_outbox|api_agent",
  "fixer": "manual_outbox|api_agent",
  "researcher": "manual_outbox"
}

budgets: { "max_outbox_prompts": int }

Rules:
- Default path for missing `artifacts/context_pack.json` is deterministic local librarian execution (`local_exec` -> `scripts/ctcp_librarian.py`).
- `librarian/context_pack` and `contract_guardian/review_contract` are hard-local roles; `mode`, `role_providers`, and `CTCP_FORCE_PROVIDER` MUST NOT remap them away from `local_exec` (except explicit `mock_agent` test mode).
- `local_exec` librarian execution MUST follow B.1/B.2 (deterministic, verbatim-only, repo-scoped read-only).
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
