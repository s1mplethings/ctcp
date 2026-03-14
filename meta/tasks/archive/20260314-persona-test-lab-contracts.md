# Task Archive - 2026-03-14 - Persona Test Lab 合同、隔离会话规则与回归资产落地

Queue Item: `ADHOC-20260314-persona-test-lab-contracts`
Status: `done`

## Summary

- 新增 `docs/14_persona_test_lab.md` 作为单一权威文档。
- 新增 `persona_lab/` 静态资产目录，包含 production persona、test user personas、rubrics 和 minimum regression cases。
- 把 persona regression 接入 core / flow / gates / support lane / artifact contracts / paths docs。
- 明确 persona-lab transcripts、scores、fail reasons、snapshots 必须写到 repo 外的 `CTCP_RUNS_ROOT`。

## Scope

- docs/meta/backlog/report/static-assets only
- no runtime runner/judge implementation
- no production state mutation

## Key Constraints

- production persona / test user persona / judge 三层分离
- fresh session per case
- English Contracts, Chinese Intent
- transcript + score + fail reasons mandatory for future executed runs

## Acceptance

- `docs/14_persona_test_lab.md` exists and is authoritative
- `persona_lab/` baseline assets exist
- `docs/03_quality_gates.md` and `docs/30_artifact_contracts.md` define persona regression acceptance
- repo-level checks and contract verify recorded in `meta/reports/LAST.md`
