# Patch-First Editing Contract

All code edits are patch-first. Agent output is accepted only as unified diff and is applied only through the patch gate.

## Required Patch Shape

1. Output must be unified diff text.
2. First non-empty line must be `diff --git ...`.
3. Per file section must include `--- a/...`, `+++ b/...`, and `@@ ... @@` hunk lines.
4. Binary patch payloads are rejected.
5. Prose-only output is rejected.

## Three Mandatory Gates

1. Path normalization gate
   - Normalize to repo-root relative POSIX paths.
   - Reject absolute paths, drive-letter paths, backtracking (`..`), or empty paths.
2. Policy gate
   - Enforce allowlist roots (`allow_roots`) and deny prefixes (`deny_prefixes`).
   - Reject denied suffixes (`deny_suffixes`), lock/binary/artifact-like targets.
   - Enforce patch size budgets: `max_files` and `max_added_lines`.
   - Default budgets: `max_files=5`, `max_added_lines=400`.
3. Apply precheck gate
   - Must pass `git apply --check` in `repo_root`.

Only after all three gates pass may the system run `git apply`.

## Execution Boundary

1. All git apply/check commands run with `cwd=repo_root`.
2. `run_dir` is evidence-only (`logs`, `outbox`, `reviews`, `artifacts`) and never used as repo root for apply/test path resolution.

## Rejection Contract

When rejected, the orchestrator must emit structured rejection evidence with:

- `stage`: `parse|policy|git_check|apply`
- `code`: stable error code (`PATCH_PARSE_INVALID`, `PATCH_POLICY_DENY`, `PATCH_GIT_CHECK_FAIL`, `PATCH_APPLY_FAIL`)
- `message`: human-readable summary
- `details`: machine-auditable fields (files, limits, command stderr tail)

`artifacts/diff.patch` (candidate patch) must still be preserved. Rejection reasons must be written to review/outbox feedback and included in failure bundle evidence.

## Retry Rule (Hard)

After rejection, agent may only resubmit `artifacts/diff.patch` as unified diff.

Not allowed:
- full-file rewrite blobs
- alternate output channel replacing patch
- bypassing `verify_repo` / workflow / contract gates
