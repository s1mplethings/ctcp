# Update 2026-03-10 - Markdown 对象状态机治理基线（6-file baseline）

### Queue Binding
- Queue Item: `ADHOC-20260310-md-object-state-machine`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

### Context
- 用户目标：把 markdown 体系从“说明书集合”升级为“对象 + 状态机管理”，防止旧流程被直接删掉和废弃对象暗中继续生效。
- 本次范围：先落地最小可用基线（registry + state machine + process/rule/strategy 三个 active 对象），不做运行时代码行为改造。
- Out of scope:
  - orchestrator/runtime 逻辑变更
  - frontend/support 链路行为改动
  - 全量历史文档一次性迁移

## Task Truth Source (single source for current task)

- task_purpose: 建立 markdown 对象状态管理基线，形成可审计的对象状态真源与转移规则。
- allowed_behavior_change:
  - 新增 `docs/10_REGISTRY.md` 与 `docs/20_STATE_MACHINE.md`。
  - 新增对象化文档：`PROC-main-workflow`、`RULE-no-direct-delete`、`STRAT-inheritance-check`。
  - 在 `docs/00_CORE.md` 增加 markdown 对象生命周期契约入口。
- forbidden_goal_shift:
  - 不得改写仓库 North Star 与 canonical 10-step 执行语义。
  - 不得把 docs 改造扩展为运行时执行重构任务。
  - 不得静默删除现有历史文档。
- in_scope_modules:
  - `docs/00_CORE.md`
  - `docs/10_REGISTRY.md`
  - `docs/20_STATE_MACHINE.md`
  - `docs/processes/PROC-main-workflow.md`
  - `docs/rules/RULE-no-direct-delete.md`
  - `docs/strategies/STRAT-inheritance-check.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `frontend/*`
  - `tools/telegram_cs_bot.py`
  - `src/` 和 `include/` 运行时代码
- completion_evidence:
  - 新增对象状态文档存在且互相引用一致。
  - triplet guard tests 通过。
  - canonical verify 已执行并记录结果（PASS 或首个失败点 + 最小修复策略）。

## Analysis / Find (before plan)

- Entrypoint analysis:
  - docs 治理入口来自 `docs/00_CORE.md` + `meta/tasks/CURRENT.md` task truth + queue 绑定。
- Downstream consumer analysis:
  - 规划/实施 agent 在改流程类文档前应先读取 registry/state-machine。
  - verify/workflow gate 消费 `meta/tasks/CURRENT.md` 与 `meta/reports/LAST.md` 证据链。
- Source of truth:
  - 对象当前状态真源：`docs/10_REGISTRY.md`。
  - 状态转移真源：`docs/20_STATE_MACHINE.md`。
  - 任务范围真源：本文件当前 update 段。
- Current break point / missing wiring:
  - 现状缺少对象状态真源，流程文档可被整体覆盖且难以追踪替代关系。
  - 缺少“禁止直接删除”硬规则与继承检查策略对象。
- Repo-local search sufficient: `yes`
- If no, external research artifact: `N/A`

## Integration Check (before implementation)

- upstream: `docs/00_CORE.md` contract reader + task binding (`meta/tasks/CURRENT.md`).
- current_module: `docs/10_REGISTRY.md` + `docs/20_STATE_MACHINE.md` + object docs (`processes/strategies/rules`).
- downstream: docs governance decisions, future process updates, and verify evidence records in `meta/reports/LAST.md`.
- source_of_truth: `docs/10_REGISTRY.md` (object state) and `docs/20_STATE_MACHINE.md` (transition legality).
- fallback: transition preconditions missing时阻断状态推进，保持原状态并要求补齐决策/证据。
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - 跳过 registry 直接宣布对象状态变更。
  - 直接 `active -> removed` 或 `active -> archived`。
  - 仅在 chat/prompt 声明废弃，不更新 registry/decision/evidence。
- user_visible_effect:
  - 文档治理改为对象状态驱动；当前正式对象一眼可查。
  - 旧流程不可再被一步删除，必须经过可审计迁移阶段。

## DoD Mapping (from request)

- [x] DoD-1: 引入状态机核心文档（registry + state machine）并定义统一状态集合。
- [x] DoD-2: 建立最小 active 对象集（process/strategy/rule）并使用唯一 ID。
- [x] DoD-3: 明确“禁止直接删除”与“继承检查”策略作为正式对象。
- [ ] DoD-4: 完成 check/fix loop + canonical verify 并记录结果。

## Acceptance (this update)

- [x] DoD written (this update section complete)
- [x] Code changes allowed (`docs/meta only`)
- [x] Doc/spec-first change included in same patch
- [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
- [x] `meta/reports/LAST.md` updated in same patch

## Plan

1) 绑定 ADHOC queue，并在 CURRENT 写入 task truth + integration check。
2) 落地 6-file baseline（registry/state machine/process/rule/strategy + core 链接入口）。
3) 执行 docs 相关 check 与 triplet guard 本地回归。
4) 运行 canonical verify 并记录首个失败点或通过结果。
5) 回填 `meta/reports/LAST.md` 与本文件 results，给出 `connected + accumulated + consumed` 证据。

## Notes / Decisions

- Default choices made: 先实施最小对象集合，不做一次性历史清理。
- Alternatives considered: 直接全量重构所有 docs 为对象化；已拒绝（改动面过大，风险高）。
- Any contract exception reference (must also log in `ai_context/decision_log.md`): None.
- Issue memory decision: 本次为 docs governance 基线建设，未观察到新的用户可见运行时故障，不新增 issue memory 条目。
- Skill decision (`skillized: yes` or `skillized: no, because ...`): skillized: no, because this patch defines repository-local governance baseline docs rather than a reusable runtime workflow asset.

## Results (2026-03-10 - Markdown object state machine baseline)

- Files changed:
  - `docs/00_CORE.md`
  - `docs/10_REGISTRY.md`
  - `docs/20_STATE_MACHINE.md`
  - `docs/processes/PROC-main-workflow.md`
  - `docs/rules/RULE-no-direct-delete.md`
  - `docs/strategies/STRAT-inheritance-check.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`

- DoD completion status:
  - [x] DoD-1: 状态机核心文档与状态集合落地。
  - [x] DoD-2: 最小 active 对象集落地并登记。
  - [x] DoD-3: no-direct-delete + inheritance-check 作为正式对象落地。
  - [ ] DoD-4: canonical verify 全量通过（当前首个失败为 lite replay S16）。

- Acceptance status:
  - [x] DoD written
  - [x] Code changes allowed (`docs/meta only`)
  - [x] Doc/spec-first change included in same patch
  - [ ] `scripts/verify_repo.*` passes（首个失败点已记录）
  - [x] `meta/reports/LAST.md` updated in same patch

- Verification summary:
  - `python scripts/workflow_checks.py` => `0` (`[workflow_checks] ok`)
  - `python scripts/sync_doc_links.py --check` => `0` (`[sync_doc_links] ok`)
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => `0` (8 passed)
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => `0` (3 passed)
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => `0` (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => `1`
    - first failure gate: `lite scenario replay`
    - first failed scenario: `S16_lite_fixer_loop_pass`
    - failure detail: `step 6: expect_exit mismatch, rc=1, expect=0`
    - evidence:
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-005420/summary.json`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-005420/S16_lite_fixer_loop_pass/TRACE.md`
      - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260310-005420/S16_lite_fixer_loop_pass/sandbox/20260310-005550-884425-orchestrate/artifacts/verify_report.json`
    - minimal repair strategy:
      - 更新 S16 fixer fixture 使其在 replay 沙箱内满足最新 `workflow_checks` 规则（补齐 `meta/tasks/CURRENT.md` docs/spec-first update 证据），避免第二轮 advance 再次触发 verify FAIL。
      - 保持修复范围在 simlab fixture/expectation，不扩展业务运行时代码。

- Queue status update suggestion (`todo/doing/done/blocked`): `blocked` (blocked by existing lite replay S16 fixture drift).

