---
name: ctcp-failure-bundle
description: Build and report a failure evidence chain after verify/gate failure, including command evidence, first failure point, and minimal next repair.
---

# ctcp-failure-bundle

## When To Use
- Verify/gate has failed and user needs evidence-chain output.
- User asks for failure bundle generation or triage artifacts.
- User explicitly invokes `$ctcp-failure-bundle`.

## When Not To Use
- Verification has not been run yet; use `ctcp-verify` first.
- User asks for full workflow execution from scratch; use `ctcp-workflow`.

## Required Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md` (if present)
- `docs/30_artifact_contracts.md` (if present)
- `meta/run_pointers/LAST_RUN.txt` (if present)

## Fixed Order
1. Re-run or reference latest verify command and return code.
2. Locate the first failing check and its source log.
3. Collect evidence pointers (trace/log/report/artifact paths available in repo/run-dir).
4. Summarize failure chain: trigger -> failing gate -> failing check -> consequence.
5. Produce minimal next repair strategy scoped to the first failure.
6. If run-dir artifacts exist, reference bundle/report paths explicitly.

## Output Discipline
- Must include command and return code.
- Must include first failure point.
- Must include exact evidence paths used.
- Must include minimal fix strategy tied to first failure only.
- Must avoid speculative broad rewrites.
