# Task - librarian-min-input-drives-apiagent

## Queue Binding
- Queue Item: `N/A (user-directed librarian minimal-input drive test)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- 用户要求验证：是否可以通过 `librarian` 的尽量少输入，驱动 `api_agent` 完成目标产物（PLAN + diff）。
- 本次任务目标：确定最小可行输入边界，并给出链路证据（成功/失败/对照）。
- 默认不改业务代码，仅执行评测并记录结论。

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: 设计并执行“librarian 最小输入 -> api_agent”链路测试矩阵（含至少 3 个最小输入场景）。
- [x] DoD-2: 给出最小可行输入（MVP input）与不可行输入边界。
- [x] DoD-3: 产出稳定性结论（重复执行 hash 一致性）与关键链路日志。
- [x] DoD-4: 运行 `scripts/verify_repo.ps1` 并将关键输出写入 `meta/reports/LAST.md`。

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local evaluation)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: 更新任务单，明确最小输入评测目标与 DoD。
2) Implement: 执行最小输入矩阵（librarian -> api_agent），沉淀 JSON 证据。
3) Verify: 运行 `scripts/verify_repo.ps1`。
4) Record: 回填 `meta/reports/LAST.md`（最小输入结论 + 可复验路径）。

## Notes / Decisions
- 默认不触碰 `src/ web/ scripts/ tools/ include/` 业务代码目录。
- API 调用使用本地 HTTP stub，确保可重复和可控。

## Results
- Completed: `meta/reports/librarian_min_input_apiagent_eval.json` generated.
- MVP minimal input found: `empty_needs` (`file_request_bytes=168`) still unblocks librarian gate and enables api_agent patch output.
- Stability: `10/10` successful repeated runs, `unique_patch_hashes=1` (stable).
- Boundary finding: even when librarian fails/skip, direct dispatch to patchmaker/api_agent can still execute (current implementation coupling is weak).
- Completed: `scripts/verify_repo.ps1` passed (workflow/contract/doc-index/tests all green).
