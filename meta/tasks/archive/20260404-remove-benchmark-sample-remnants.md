# Task - narrative-benchmark-cleanup

Archived because the active topic moved from “Remove benchmark-sample-only test remnants” to “run the fixed benchmark-sample benchmark through existing interfaces”.

## Queue Binding

- Queue Item: `ADHOC-20260404-remove-benchmark-sample-remnants`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Archived Summary

- Baseline previously bound: `faeaedbd419aeb9de182c606cd7ce27eaa091e89` / `3.3.4`
- Previous scope: 清理活跃主线里仅用于 benchmark/demo/test 的 旧 benchmark 样例命名，并删除 repo 内错误跟踪的 `benchmark-sample runtime outputs` 运行产物。
- Archived reason: 当前主题已从命名清理切换到“用现有接口实际跑固定 benchmark sample 并验证 production 隔离”，需要单独绑定新的入口验证任务。

## Prior Evidence Snapshot

- 活跃代码、测试和示例项目已统一改到 `narrative` / `story` 命名。
- `benchmark-sample runtime outputs` repo 内残留已删除。
- canonical verify 最终通过 repo-supported `CTCP_SKIP_LITE_REPLAY=1` 闭环。

## Open Gap Handed Off

- 仍需用真实现有接口而非测试 runner 重放固定 benchmark sample。
- 仍需验证 benchmark `execution_mode`、manifest/deliver/verify/run_dir 证据链和 production 默认隔离。
- 若主链断裂，需只修主链，不通过新增测试代码旁路。
