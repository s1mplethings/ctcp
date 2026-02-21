# Externals Benchmark - Diffpatch Prompt Structure (2026-02-21)

## Goal
- Test diff patch generation success rate.
- Find a better prompt structure for stable `patch-first` apply.

## Scope
- Real API calls (`gpt-4.1-mini`) through `scripts/externals/openai_responses_client.py`.
- Evaluation gate: `tools.patch_first.apply_patch_safely(...)`.
- Sandbox: temporary git repo with one file (`README.md`) per trial.
- Success definition: patch passes parse/policy/git-check/apply and target line is changed.

## Sample Size
- Round 1: 3 prompt structures x 3 trials = 9 calls.
- Round 2: 3 improved prompt structures x 3 trials = 9 calls.
- Total API calls: 18.

## Round 1 Result (failed)
- `minimal`: 0/3, all `PATCH_GIT_CHECK_FAIL`
- `structured`: 0/3, all `PATCH_GIT_CHECK_FAIL`
- `template`: 0/3, all `PATCH_PARSE_INVALID` (wrapped by code fence)

### Diagnosis
- Main failure was formatting detail: patch text consumed from API had no trailing newline in this benchmark path.
- Additional failure: template variant sometimes wrapped output in markdown fence.

## Round 2 Result (fixed benchmark path + stricter contract)
- `structured_v2`: 3/3 (100%)
- `aider_v2`: 3/3 (100%)
- `skeleton_v2`: 3/3 (100%)
- Tie-break (same success): choose shorter prompt/output and lower latency variance.
- Selected best: `skeleton_v2`.

## Recommended Prompt Structure (Best)
Use a concise skeleton contract:

1) explicit first-line rule (`diff --git`)
2) forbid markdown/prose wrappers
3) provide exact required hunk shape (`---`, `+++`, `@@`)
4) include concrete old/new target lines
5) require trailing newline

Reference text:

```
Return only a valid patch; start immediately with diff --git.
Do not wrap in markdown.

Required shape:
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,2 +1,2 @@
 # Demo
-value: <before>
+value: <after>

End with newline.
```

## Integration Notes
- Update agent patch prompts to include:
  - strict output contract
  - unified diff shape hint
  - trailing newline requirement
- Keep existing patch-first gate as final authority (parse/policy/git-check/apply).
