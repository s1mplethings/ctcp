---
name: ctcp-patch-guard
description: Validate patch scope and policy compliance before/after apply, then report first violation and smallest repair path.
---

# ctcp-patch-guard

## When To Use
- User asks to validate whether a patch is policy-safe for CTCP contracts.
- A patch is rejected by scope/contract guard and needs focused triage.
- When invoked explicitly with `$ctcp-patch-guard`.

## When Not To Use
- No patch/diff is involved.
- User asks only for full workflow execution (`ctcp-workflow`).

## Required Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `contracts/allowed_changes.yaml` (if present)
- `tools/contract_guard.py`
- `tools/patch_first/` (if present)

## Fixed Order
1. Confirm allowed/blocked scope from policy files.
2. Run patch guard/contract checks for current working diff.
3. Identify first violating file/rule and rejection reason.
4. Propose minimal patch rewrite strategy for that first violation.
5. Re-run verify gate after guard passes.
6. Report command/rc/first violation/minimal fix.

## Output Discipline
- Log exact guard/check commands and return codes.
- Report first failing policy rule and touched file path.
- Keep fix strategy minimal and rule-targeted.
- Do not broaden patch scope during remediation.
