Artifact Contracts (v0.1)

All files live under the external run directory unless stated otherwise.

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

I) artifacts/verify_report.json

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

J) events.jsonl

Each line:

{"ts":"...","role":"...","event":"...","path":"..."}

K) artifacts/dispatch_config.json

Fields:

schema_version: "ctcp-dispatch-config-v1"

mode: "manual_outbox" | "ollama_agent" | "api_agent" | "local_exec"

role_providers: {
  "librarian": "local_exec|manual_outbox",
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
- Manual outbox for librarian is allowed only when explicitly configured (`mode: manual_outbox` and `role_providers.librarian: manual_outbox`).
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
