# Agent TeamNet (ADLC Mainline)

目标：给任意 AI 一个最小但完整的团队协作拓扑，明确谁负责什么、谁能决策、产物落在哪里。

## TeamNet role graph (mesh)

```text
 +------------------+      +------------------+      +------------------+
 |  Local Librarian |----->|    Blackboard    |<-----|    Researcher    |
 | read-only supply |      | work + artifacts |      | externals summary|
 +---------+--------+      +---------+--------+      +---------+--------+
           |                         |                         |
           v                         v                         v
 +---------+--------+      +---------+--------+      +---------+--------+
 | ContractGuardian |----->| Chair/Planner    |<-----| CostController   |
 | adversarial DoD  |      | ONLY decision    |      | adversarial cost |
 +------------------+      +----+--------+----+      +------------------+
                                 |        |
                                 v        v
                          +------+--+  +--+---------------+
                          |PatchMaker|  |  Local Verifier |
                          | execute  |  |  fact judge     |
                          +----+-----+  +--------+--------+
                               ^                 |
                               |                 v
                               |        +--------+--------+
                               +--------+     Fixer       |
                                        | execute (bundle)|
                                        +-----------------+
```

角色要点：
- Local Librarian：只读仓库，负责 context_pack/file_supply，减少 API 文件读取成本。
- Researcher：仅补充 externals 摘要；`find` 主链路仍是本地 workflow resolver。
- Blackboard：统一工作区与产物交换面。
- ContractGuardian：对抗式检查 contract/DoD/gate。
- CostController：对抗式限制 token、调用次数、读文件预算（通过 Chair 施加约束）。
- Chair/Planner：唯一决策点。
- PatchMaker/Fixer：执行角色，Fixer 只基于 failure bundle 修复。
- Local Verifier：事实判定，运行 `verify_repo`/SimLab。

## ADLC mainline with agent assists

```text
doc -> analysis -> find -> plan -> build/verify -> contrast -> fix -> deploy/merge
  |       |         |       |           |            |        |         |
  |       |         |       |           |            |        |         +--> artifacts/release_report.md
  |       |         |       |           |            |        +------------> artifacts/diff.patch (new)
  |       |         |       |           |            +---------------------> failure_bundle.zip (input to Fixer)
  |       |         |       |           +----------------------------------> TRACE.md + artifacts/verify_report.md
  |       |         |       +-----------------------------------------------> artifacts/PLAN.md
  |       |         +-------------------------------------------------------> artifacts/find_result.json
  |       +-----------------------------------------------------------------> artifacts/analysis.md
  +-------------------------------------------------------------------------> artifacts/guardrails.md

* ONLY decision point across steps: Chair/Planner
```

产物映射（与 `docs/00_CORE.md` 第 4/5 节一致）：
- doc -> `artifacts/guardrails.md`
- analysis -> `artifacts/analysis.md`
- find -> `artifacts/find_result.json`
- plan -> `artifacts/PLAN.md`
- build/verify -> `TRACE.md`, `artifacts/verify_report.md`
- contrast/fix -> `failure_bundle.zip` -> `artifacts/diff.patch`
- deploy/merge -> `artifacts/release_report.md`
