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

C) artifacts/context_pack.json (Librarian output)

Fields:

schema_version: "ctcp-context-pack-v1"

goal

repo_slug

summary

files[]: { "path": "...", "why": "...", "content": "..." }

omitted[]: { "path": "...", "reason": "too_large|denied|irrelevant" }

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

Gates: (lite must exist)

Stop: (stop conditions)

Budgets: (iterations/files/bytes)

Steps: (patch -> verify loop)

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

mode: "manual_outbox" | "local_exec" | "api_agent"

role_providers: {
  "librarian": "local_exec|manual_outbox",
  "chair": "manual_outbox|api_agent",
  "contract_guardian": "manual_outbox|local_exec",
  "cost_controller": "manual_outbox",
  "patchmaker": "manual_outbox|api_agent",
  "fixer": "manual_outbox|api_agent",
  "researcher": "manual_outbox"
}

budgets: { "max_outbox_prompts": int }

Rules:
- `local_exec` MUST only auto-execute `librarian` or `contract_guardian`.
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
