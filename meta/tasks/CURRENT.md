# Task - lite-agent-link-and-adlc-robustness-tests

## Queue Binding
- Queue Item: `N/A (user-directed deterministic lite simlab expansion)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- 目标是为 orchestrator/dispatch 链路补齐 deterministic 的 lite 场景覆盖：角色连接性（outbox prompt）+ 鲁棒性（幂等、坏输入、scope 违规）。
- 必须保持 patch-first 与 artifact contract，不引入联网调用与新依赖。
- verify 路径必须保持 `python simlab/run.py --suite lite` 与 `scripts/verify_repo.*` 可通过。

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: 新增 lite 场景 S17~S25（连接性 + 鲁棒性）并全部 deterministic。
- [x] DoD-2: blocked gate 对应角色可稳定产出 outbox prompt（至少覆盖 chair/researcher/librarian/guardian/cost/patchmaker/fixer）。
- [x] DoD-3: SimLab lite 全量回放通过（包含新增场景）。
- [x] DoD-4: `python -m compileall .` 与 `scripts/verify_repo.ps1` 通过。

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local issue)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first（任务单 + 契约核对 + 场景设计）
2) Implement（新增 S17~S25；必要时 orchestrator 最小修补）
3) Verify（compileall + simlab lite + verify_repo）
4) Record（更新 LAST 报告与验收摘要）

## Notes / Decisions
- 不新增依赖，不引入联网调用，场景中通过离线 artifact 注入触发 gate。
- 优先通过 scenario 配置满足连接性，代码仅做必要修补。

## Results
- PASS: 新增 S17~S25 后，`simlab --suite lite` 通过（17/17）。
- PASS: `python -m compileall .` 与 `powershell -ExecutionPolicy Bypass -File scripts\\verify_repo.ps1` 通过。
