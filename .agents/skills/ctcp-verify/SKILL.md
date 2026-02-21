---
name: ctcp-verify
description: Run the repo acceptance gate via verify_repo, capture auditable results, and report the first failure with minimal-fix guidance.
---

# ctcp-verify

## When To Use
- User asks for gate/acceptance verification.
- User asks to validate the current patch against repo rules.
- User explicitly invokes `$ctcp-verify`.

## When Not To Use
- User asks for full end-to-end workflow orchestration; use `ctcp-workflow`.
- User asks only for failure evidence packaging after a known failure; use `ctcp-failure-bundle`.

## Required Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md` (if present)
- `PATCH_README.md`

## Fixed Order
1. Select verify entrypoint by OS:
2. Windows: `scripts/verify_repo.ps1`
3. Unix: `scripts/verify_repo.sh`
4. Execute verify and capture stdout/stderr and return code.
5. Extract first failing gate/check (workflow/contract/doc-index/build/test).
6. Report minimal, scoped repair strategy.

## Output Discipline
- Must include executed command.
- Must include command return code.
- Must include first failure location/message.
- Must include minimal repair plan focused only on that failure.
- Must not propose unrelated cleanup.
