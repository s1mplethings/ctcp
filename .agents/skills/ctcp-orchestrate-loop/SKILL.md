---
name: ctcp-orchestrate-loop
description: Drive the CTCP orchestrator state loop (status/advance/verify) with deterministic gate handling and auditable step logs.
---

# ctcp-orchestrate-loop

## When To Use
- User wants artifact-driven loop execution under `scripts/ctcp_orchestrate.py`.
- User asks to advance a run through blocked/ready/verify states.
- When invoked explicitly with `$ctcp-orchestrate-loop`.

## When Not To Use
- No run context and no intent to orchestrate run state.
- User asks only for a direct one-shot verify (`ctcp-verify`).

## Required Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md` (if present)
- `docs/03_quality_gates.md` (if present)
- `scripts/ctcp_orchestrate.py`
- `meta/run_pointers/LAST_RUN.txt` (if present)

## Fixed Order
1. Check run state: `python scripts/ctcp_orchestrate.py status`.
2. Advance loop deterministically: `python scripts/ctcp_orchestrate.py advance`.
3. Evaluate gate transition and first blocking reason.
4. Run verify gate when state reaches verify-ready path.
5. On failure, switch to evidence-chain reporting (`ctcp-failure-bundle`).
6. Report trace with command/rc/first fail/minimal next fix.

## Output Discipline
- Include every orchestrator command and return code.
- Identify first blocking gate reason/path.
- Keep interventions minimal and state-driven.
- Do not change unrelated artifacts or code paths.
