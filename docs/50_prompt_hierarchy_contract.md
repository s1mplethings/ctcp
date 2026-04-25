# Prompt Hierarchy Contract

This document defines prompt-source authority for CTCP.
If it conflicts with `AGENTS.md`, `AGENTS.md` wins.

## 1) Root Authority

- `AGENTS.md` is the root contract.
- Routed lane/runtime documents and `meta/tasks/CURRENT.md` refine execution for the current concern or bound task.
- `PROMPT.md` is never a parallel authority source.

## 2) Source Order

Prompt compilation must respect this order:

1. `AGENTS.md`
2. routed contract for the active concern/lane/runtime surface
3. `meta/tasks/CURRENT.md`
4. compiled prompt artifacts such as `${run_dir}/PROMPT.md`

If two layers conflict, the higher layer wins.

## 3) Compiled Prompt Status

- `${run_dir}/PROMPT.md` is a compiled/derived artifact.
- It may package root/routed/task constraints for the coding agent.
- It must not introduce new top-level rules that override the root contract.
- It must not expand write scope beyond `meta/tasks/CURRENT.md`.

## 4) Questions Artifact Status

- `${run_dir}/QUESTIONS.md` is a blocking-question artifact for that run.
- It may surface unresolved blockers.
- It must not redefine repo authority, bypass verify, or override the active task card.

## 5) Verify Surface

The hierarchy is enforced by:

- `scripts/prompt_contract_check.py`
- `tests/test_prompt_contract_check.py`
- `docs/10_team_mode.md`

Any document that describes `PROMPT.md` as the unique entry, unique authority, or an independent rule source is a contract failure.
