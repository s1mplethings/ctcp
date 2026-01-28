
# Summary / Drill-down（默认不可能堆在一起）

## 目标
1) 启动时只显示“大类网状图”（Summary），节点很少，必然不卡、也不会堆成一团
2) 点击某个大类进入子图（Drill-down），再看具体联系
3) 可变（mutable）的东西在主图里；不变（immutable）的默认放在 Settings/Library

## 大类（建议默认）
- category.Docs
- category.Modules
- category.Contracts
- category.Meta
- category.Runs
- category.Gates

## 展示规则
### Summary（默认启动）
- nodes：仅 category 节点 + pinned 核心节点（可选）
- edges：仅聚合边（aggregate=true），表示“有多少条真实边被汇总”
- layout：固定网格（手工坐标 / preset），不跑任何力导向

### Detail（点击后）
- Pipeline：Phase 分块 + type 行顺序 A（Doc/Module/Contract/…）
- Docs：Doc + docs_link
- Contracts：Contract + producer/consumer

## 可变性
- tier=core + mutable=true：默认显示在主图（可展开/可编辑）
- tier=settings + mutable=false：默认折叠在侧库，仅预览
