---
name: ctcp-gate-precheck
description: Run pre-change CTCP gates and contract preconditions before implementation to avoid invalid edits and wasted verify cycles.
---

# ctcp-gate-precheck

## When To Use
- Before any code change in a CTCP task.
- When user asks to check if edits are currently allowed by repository rules.
- When invoked explicitly with `$ctcp-gate-precheck`.

## When Not To Use
- User only wants full end-to-end execution (`ctcp-workflow`).
- User only wants final acceptance check (`ctcp-verify`).

## Required Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md` (if present)
- `docs/03_quality_gates.md` (if present)
- `meta/tasks/CURRENT.md`

## Fixed Order
1. Spec-first: verify docs/spec/meta constraints for the current task.
2. Gate precheck: validate task gate and required contract files.
3. Confirm code-change permission (`[x] Code changes allowed`) before touching code paths.
4. If precheck fails, stop and report first failure with evidence.
5. If precheck passes, continue to verify/report flow.

## Output Discipline
- Include each command executed and its return code.
- Name the first failed gate/check path and message.
- Provide the minimum viable fix to clear that first failure.
- Avoid unrelated edits or cleanup.
