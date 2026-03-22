# Skills Index

> Quick lookup only. Read individual `SKILL.md` for full trigger rules, inputs, and outputs.

| Skill | Invoke | When to use |
|-------|--------|-------------|
| `ctcp-workflow` | `$ctcp-workflow` | End-to-end CTCP/ADLC execution with spec-first discipline, gates, and reporting |
| `ctcp-verify` | `$ctcp-verify` | Run gate/acceptance verification or validate a patch against repo rules |
| `ctcp-gate-precheck` | `$ctcp-gate-precheck` | Check if code edits are currently allowed before making any change |
| `ctcp-patch-guard` | `$ctcp-patch-guard` | Validate patch policy-safety or triage scope/contract guard rejection |
| `ctcp-failure-bundle` | `$ctcp-failure-bundle` | Package failure evidence chain after a verify/gate failure |
| `ctcp-run-report` | `$ctcp-run-report` | Produce structured run summary and closure note after execution/verify |
| `ctcp-simlab-lite` | `$ctcp-simlab-lite` | Lightweight scenario replay for quick regression evidence |
| `ctcp-orchestrate-loop` | `$ctcp-orchestrate-loop` | Advance a run through blocked/ready/verify states via orchestrate loop |
| `ctcp-doc-index-sync` | `$ctcp-doc-index-sync` | Sync README doc index when doc-index check fails in verify |

## Decision guide

```
Need to run the full workflow?          → ctcp-workflow
Need to run verify only?               → ctcp-verify
About to make code changes?            → ctcp-gate-precheck first
Patch rejected by scope guard?         → ctcp-patch-guard
Verify failed, need evidence package?  → ctcp-failure-bundle
Verify passed, need closure report?    → ctcp-run-report
Need regression proof via SimLab?      → ctcp-simlab-lite
Need to advance a stalled run?         → ctcp-orchestrate-loop
Doc index check failed?                → ctcp-doc-index-sync
```
