---
name: ctcp-workflow
description: Run the repo-standard CTCP/ADLC execution workflow with spec-first discipline, gates, verification, and auditable reporting.
---

# ctcp-workflow

## When To Use
- User asks for end-to-end CTCP/ADLC execution.
- User asks to run the fixed repo workflow before/while implementing changes.
- User explicitly invokes `$ctcp-workflow`.

## When Not To Use
- Request is only about running acceptance checks; use `ctcp-verify`.
- Request is only about failure evidence packaging; use `ctcp-failure-bundle`.
- Request is pure Q&A with no workflow execution.

## Required Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md` (if present)
- `docs/03_quality_gates.md` (if present)
- `PATCH_README.md`
- `TREE.md` (if present)
- `ai_context/problem_registry.md` (if present)
- `ai_context/decision_log.md` (if present)

## Fixed Order
1. Spec-first: align docs/spec/meta constraints before code.
2. Gate precheck: confirm task gate and code-change permission state.
3. Execute minimal implementation for the current goal.
4. Verify via repo gate entrypoint (`scripts/verify_repo.ps1` on Windows, `scripts/verify_repo.sh` on Unix).
5. Report: record command, return code, first failing point, and minimal repair strategy.
6. If failed, switch to failure evidence chain (`ctcp-failure-bundle`).

## Output Discipline
- Always log exact commands executed.
- Always record return code for each gate/verify command.
- Always identify the first failing gate/check.
- Always propose the smallest viable repair scoped to that first failure.
- Never include unrelated refactors or dependency changes.
