# Task Archive - 2026-03-15 - Persona Test Lab fixture runner / judge 基线落地

Queue Item: `ADHOC-20260315-persona-test-lab-runner-judge`
Status: `done`

## Summary

- 从 docs/static-assets 继续推进 Persona Test Lab，新增最小可执行 fixture runner / judge。
- 每个 case 必须 fresh session，并输出 transcript/score/fail reasons/summary 到 repo 外。
- 当前只做 fixture reply baseline，不接 live production assistant。

## Scope

- `scripts/ctcp_persona_lab.py`
- `tests/test_persona_lab_runner.py`
- authority docs / issue memory / CURRENT / LAST / queue updates

## Key Constraints

- fresh-session-per-case
- repo-external run artifacts only
- `source_version` from root `VERSION`
- `source_commit=unknown` only when git SHA cannot be resolved
- no production support state mutation

## Acceptance

- runner writes root manifest/summary plus per-case transcript/score/fail reasons/summary
- tests prove pass path, fail-fast path, and session isolation
- docs mark fixture baseline as current and live adapter as pending
- workflow/contract/doc-index/triplet/canonical verify evidence is recorded in `meta/reports/LAST.md`
