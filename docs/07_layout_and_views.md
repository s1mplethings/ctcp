
# Layout & Views（效果硬规则）

> 默认启动必须是 Summary（大类网状图），避免全量加载导致卡顿与叠在一起。

你选的是 **A：类型固定顺序**，所以 Pipeline View 必须：
- Phase 分块分开（不允许挤在一起）
- 块内按固定行顺序：Doc → Module → Contract → Gate → Run
- 默认 preset（positions 来自 LayoutEngine/meta.positions）
- 默认禁止 cose/fcose（仅可手动触发）

## Views
### Pipeline（默认）
- nodes: Phase + Module + Contract（可选 Gate/Run）
- edges: produces/consumes/verifies
- layout: preset
- grouping: phase（compound nodes）

### Docs
- nodes: Doc
- edges: docs_link

### Contracts
- nodes: Contract + Modules
- edges: produces/consumes

## Layout 缓存（解决“非常卡”）
- positions 必须写回：meta/pipeline_graph.json -> positions
- 二次打开直接 preset（秒开）


## Summary（默认启动）
- nodes: category.*（≤ 12） + pinned core nodes（可选）
- edges: aggregate edges（weight 表示汇总数量）
- layout: preset 固定网格（不允许力导向）
- click: drill-down（进入 Pipeline/Docs/Contracts 子图）
