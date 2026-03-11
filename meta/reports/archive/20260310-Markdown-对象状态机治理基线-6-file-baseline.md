# Update 2026-03-10 - Markdown 对象状态机治理基线（6-file baseline）

### Readlist
- `docs/00_CORE.md`
- `docs/01_north_star.md`
- `docs/04_execution_flow.md`
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `docs/20_conventions.md`
- `.agents/skills/ctcp-workflow/SKILL.md`

### Plan
1) 绑定 `ADHOC-20260310-md-object-state-machine` 到 queue + CURRENT，并补齐 task truth/integration check。
2) 按最小可落地范围新增 state-machine 文档骨架（registry + state machine + process/rule/strategy 对象）。
3) 在 `docs/00_CORE.md` 建立 markdown 对象生命周期契约入口。
4) 执行 check/fix loop（workflow/doc-index + triplet guard）。
5) 执行 canonical verify，记录首个失败点或通过结果。

### Changes
- `docs/00_CORE.md`
  - 新增 markdown object lifecycle contract 引用与强约束（state 真源、转移真源、禁止跳级删除、强制删除路径）。
- `docs/10_REGISTRY.md` (new)
  - 建立对象状态单一真源，登记三个 active 对象（`PROC-main-workflow`、`STRAT-inheritance-check`、`RULE-no-direct-delete`）。
- `docs/20_STATE_MACHINE.md` (new)
  - 定义状态集合、允许/禁止转移、每个转移的证据要求与运行时解释。
- `docs/processes/PROC-main-workflow.md` (new)
  - 定义 docs 治理主流程对象（输入/输出/步骤/依赖/退出条件）。
- `docs/rules/RULE-no-direct-delete.md` (new)
  - 定义 active 对象不可直接删除及删除前置条件。
- `docs/strategies/STRAT-inheritance-check.md` (new)
  - 定义继承检查策略，防止目标漂移与隐式规则丢失。
- `meta/backlog/execution_queue.json`
  - 新增队列项 `ADHOC-20260310-md-object-state-machine`（DoD、产物、测试清单）。
- `meta/tasks/CURRENT.md`
  - 新增本轮 Queue Binding / Task Truth / Analysis / Integration Check / DoD/Plan/Notes。

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task card: `meta/tasks/CURRENT.md`
- Queue item: `meta/backlog/execution_queue.json`

### Integration Proof

- upstream: docs governance change request -> canonical flow step `spec -> implement`.
- current_module: `docs/10_REGISTRY.md` + `docs/20_STATE_MACHINE.md` + object docs (`PROC-main-workflow`, `RULE-no-direct-delete`, `STRAT-inheritance-check`).
- downstream: future doc/process updates must read active object states and legal transitions before modification; evidence recorded in `meta/tasks/CURRENT.md` and `meta/reports/LAST.md`.
- source_of_truth: `docs/10_REGISTRY.md` for object current state, `docs/20_STATE_MACHINE.md` for transition legality.
- fallback: if transition prerequisites are missing, object state does not move and change is blocked until decision/evidence is complete.
- acceptance_test:
  - `python scripts/workflow_checks.py`
  - `python scripts/sync_doc_links.py --check`
  - `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
  - `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- forbidden_bypass:
  - skip registry and edit process semantics directly
  - direct transition `active -> removed` or `active -> archived`
  - deprecate by prose only without registry/decision/evidence update
- user_visible_effect: active流程/策略/规则可在 registry 直接定位；旧流程不能被一步删除，必须走阶段迁移。

### Verify
- `python scripts/workflow_checks.py` => exit `0` (`[workflow_checks] ok`)
- `python scripts/sync_doc_links.py --check` => exit `0` (`[sync_doc_links] ok`)
- `python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` => exit `0` (8 passed)
- `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` => exit `0` (3 passed)
- `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` => exit `0` (3 passed)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit `1`
  - first failure gate: `lite scenario replay`
  - first failed scenario: `S16_lite_fixer_loop_pass`
  - failure detail: `step 6: expect_exit mismatch, rc=1, expect=0`
  - evidence:
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-005420/summary.json`
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260310-005420/S16_lite_fixer_loop_pass/TRACE.md`
    - `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_external_runs/20260310-005420/S16_lite_fixer_loop_pass/sandbox/20260310-005550-884425-orchestrate/artifacts/verify_report.json`
  - minimal fix strategy:
    - update S16 fixer replay fixture/expectation to satisfy current `workflow_checks` requirement (`meta/tasks/CURRENT.md` docs/spec-first update evidence).
    - keep fix scope limited to simlab fixture and assertions.

